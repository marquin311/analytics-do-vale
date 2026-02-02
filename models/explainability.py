import pandas as pd
import joblib
import shap
import matplotlib.pyplot as plt
import os
from database import get_engine
from config import FEATURES_MODEL, settings
from features.engine import prepare_data_for_ml

def explain_model():
    print("🕵️ Iniciando Análise de Explicabilidade por Role (SHAP)...")
    
    # 1. Carregar Modelo
    try:
        model_path = settings['model']['filename']
        model = joblib.load(model_path)
        print(f"   🧠 Modelo carregado de: {model_path}")
    except FileNotFoundError:
        print(f"❌ Modelo não encontrado em {model_path}. Treine primeiro!")
        return

    engine = get_engine()
    
    # 2. Carregar Dados (Amostra Aumentada para ter volume em todas as roles)
    query = """
    SELECT 
        p.*,
        (SELECT COUNT(*) FROM fact_kill_events k 
         WHERE k.match_id = p.match_id AND k.killer_puuid = p.puuid 
         AND k.event_time_min <= 15
         AND ((p.team_id = 100 AND (k.pos_x > 8000 OR k.pos_y > 8000)) OR 
              (p.team_id = 200 AND (k.pos_x < 7000 OR k.pos_y < 7000)))) as invade_kills
    FROM fact_match_player_performance p
    WHERE p.team_position != 'UNKNOWN' AND p.team_position != ''
    ORDER BY p.game_start_timestamp DESC
    LIMIT 6000
    """
    
    print("   📥 Baixando amostra de dados...")
    df_raw = pd.read_sql(query, engine)
    
    # 3. Engenharia de Features
    print("   ⚙️ Calculando features avançadas (v7.0)...")
    df_processed = prepare_data_for_ml(df_raw)
    
    # Preparar Explainer (baseado no modelo treinado)
    explainer = shap.TreeExplainer(model)
    
    output_dir = os.path.join("models", "artifacts")
    os.makedirs(output_dir, exist_ok=True)
    
    # 4. Loop por Role
    roles = ['TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY']
    
    for role in roles:
        print(f"\n   🔎 Analisando Role: {role}...")
        
        # Filtrar apenas a role atual
        df_role = df_processed[df_processed['team_position'] == role]
        
        if len(df_role) < 100:
            print(f"      ⚠️ Poucos dados para {role} ({len(df_role)}). Pulando.")
            continue
            
        X_role = df_role[FEATURES_MODEL]
        
        # Calcular SHAP específico para essa amostra
        shap_values = explainer.shap_values(X_role)
        
        # Gerar Gráfico
        plt.figure(figsize=(10, 14)) # Vertical um pouco maior
        plt.title(f"Fatores de Vitória: {role} (v7.0)", fontsize=16)
        
        # Summary Plot
        shap.summary_plot(shap_values, X_role, show=False, max_display=20)
        
        # Salvar
        output_file = os.path.join(output_dir, f"feature_importance_{role}.png")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close() # Limpar memória para o próximo loop
        
        print(f"      ✅ Gráfico salvo: {output_file}")

    print("\n🏁 Análise concluída! Abra a pasta 'models/artifacts' para ver os 5 gráficos.")

if __name__ == "__main__":
    explain_model()