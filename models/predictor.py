import pandas as pd
import numpy as np
import joblib
from sqlalchemy import text

from database import get_engine
from config import FEATURES_MODEL, MODEL_FILENAME
from features.engine import prepare_data_for_ml
from features.post_processing import calculate_ai_score

# Constante de Versionamento
MODEL_VERSION = 'v8.0'

def get_new_matches(engine, limit=50000):
    """
    Busca partidas pendentes usando LEFT JOIN (Mais robusto que NOT IN).
    """
    # 1. Debug: Contagem Rápida
    with engine.connect() as conn:
        total_source = conn.execute(text("SELECT COUNT(DISTINCT match_id) FROM fact_match_player_performance")).scalar()
        
        # Verifica se a tabela de predições existe antes de contar
        try:
            total_preds = conn.execute(text("SELECT COUNT(DISTINCT match_id) FROM fact_match_predictions")).scalar()
        except:
            total_preds = 0 # Tabela ainda não existe
            
        print(f"   📊 DIAGNÓSTICO: Origem={total_source} jogos | Já Previstos={total_preds} jogos")
        
        if total_source == 0:
            print("   ⚠️ AVISO: Sua tabela de performance está VAZIA! Baixe jogos primeiro.")
            return pd.DataFrame()

    # 2. Query com LEFT JOIN (Anti-Join Pattern)
    # Traz tudo da tabela 'p' (Performance) que NÃO tem correspondência na tabela 'pred' (Predictions)
    query = f"""
    SELECT 
        p.*,
        (SELECT COUNT(*) FROM fact_kill_events k 
         WHERE k.match_id = p.match_id AND k.killer_puuid = p.puuid 
         AND k.event_time_min <= 15
         AND ((p.team_id = 100 AND (k.pos_x > 8000 OR k.pos_y > 8000)) OR 
              (p.team_id = 200 AND (k.pos_x < 7000 OR k.pos_y < 7000)))) as invade_kills
    FROM fact_match_player_performance p
    LEFT JOIN fact_match_predictions pred 
        ON p.match_id = pred.match_id 
        AND p.puuid = pred.puuid
    WHERE p.team_position != 'UNKNOWN'
      AND pred.match_id IS NULL -- <--- O PULO DO GATO: Só traz o que não existe lá
    ORDER BY p.game_start_timestamp DESC
    LIMIT {limit}
    """
    
    return pd.read_sql(query, engine)

def run_predictions():
    print(f"🔮 Iniciando Pipeline de Predição ({MODEL_VERSION})...")
    engine = get_engine()
    
    # 1. Carregar Modelo
    try:
        model = joblib.load(MODEL_FILENAME)
    except FileNotFoundError:
        print("❌ Modelo não encontrado. Rode 'python main.py train' primeiro!")
        return

    # 2. Carregar Apenas Dados Novos (Incremental)
    print("   📥 Buscando partidas pendentes no PostgreSQL...")
    df_raw = get_new_matches(engine)
    
    if df_raw.empty:
        print("   ✅ Todas as partidas já estão atualizadas (ou banco vazio). Nada a fazer.")
        return

    print(f"   ⚙️ Processando {len(df_raw)} novas linhas de performance...")

    # 3. Engenharia de Features
    df_processed = prepare_data_for_ml(df_raw)
    
    # 4. Predição (Win Probability)
    X = df_processed[FEATURES_MODEL]
    probs = model.predict_proba(X)[:, 1]
    df_processed['win_prob'] = probs
    
    # 5. Cálculo do AI Score (0-100)
    print("   🧮 Calculando AI Scores e Métricas Relativas...")
    df_scores = calculate_ai_score(df_processed)
    
    # 6. Montagem do Output Final
    output_df = pd.DataFrame()
    output_df['match_id'] = df_processed['match_id']
    output_df['puuid'] = df_processed['puuid']
    output_df['game_start_timestamp'] = df_processed['game_start_timestamp'] 
    output_df['team_position'] = df_processed['team_position'] 
    
    # Métricas do Modelo
    output_df['win_probability'] = df_processed['win_prob'].round(4)
    output_df['ai_score'] = df_scores['ai_score']
    output_df['ai_rank'] = df_scores['ai_rank']
    
    # Versionamento
    output_df['model_version'] = MODEL_VERSION
    
    # 7. Normalização Relativa Global
    def get_global_zscore(row):
        # Constantes Globais (Hardcoded do Treino)
        GLOBAL_STATS = {
            'TOP':     {'mean': 52.0, 'std': 14.5},
            'JUNGLE':  {'mean': 51.5, 'std': 15.0},
            'MIDDLE':  {'mean': 50.0, 'std': 16.0},
            'BOTTOM':  {'mean': 51.0, 'std': 14.0},
            'UTILITY': {'mean': 49.5, 'std': 13.5}
        }
        role = row['team_position']
        score = row['ai_score']
        stats = GLOBAL_STATS.get(role, {'mean': 50, 'std': 15})
        return (score - stats['mean']) / stats['std']

    output_df['ai_score_role_norm'] = output_df.apply(get_global_zscore, axis=1).round(2)

    # Texto Descritivo
    conditions = [
        (output_df['ai_rank'].str.contains('S')),
        (output_df['ai_rank'].str.contains('A')),
        (output_df['ai_rank'].str.contains('B')),
        (output_df['ai_rank'].str.contains('C'))
    ]
    choices = ['MVP (Smurf)', 'Bom (Carry)', 'Neutro', 'Ruim (Tilt)']
    output_df['ai_rating_text'] = np.select(conditions, choices, default='Neutro')
    
    # 8. Salvamento Incremental (Append)
    print(f"   💾 Gravando {len(output_df)} registros em 'fact_match_predictions'...")
    
    output_df.to_sql(
        'fact_match_predictions', 
        engine, 
        if_exists='append', 
        index=False,
        chunksize=1000 
    )
    print("✅ Pipeline concluído com sucesso.")

if __name__ == "__main__":
    run_predictions()