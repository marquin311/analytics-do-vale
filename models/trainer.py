import pandas as pd
import joblib
import matplotlib.pyplot as plt
import os
from datetime import datetime
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, brier_score_loss
from sklearn.calibration import calibration_curve

from database import get_engine
from config import settings, FEATURES_MODEL, MODEL_FILENAME
from features.engine import prepare_data_for_ml

def train_model():
    print("🎓 Iniciando Treinamento (Protocolo Temporal + Calibração)...")
    engine = get_engine()
    
    # Query padrão
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
    ORDER BY p.game_start_timestamp ASC
    """
    
    df_raw = pd.read_sql(query, engine)
    
    if len(df_raw) < 50:
        print(f"❌ Dados insuficientes ({len(df_raw)}).")
        return

    # Engenharia
    df_processed = prepare_data_for_ml(df_raw)
    df_processed = df_processed.sort_values('game_start_timestamp')
    
    X = df_processed[FEATURES_MODEL]
    y = df_processed['win'].astype(int)
    roles = df_processed['team_position']

    # Split Temporal (80/20)
    split_idx = int(len(df_processed) * 0.8)

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    roles_test = roles.iloc[split_idx:]
    
    # Treinamento
    print(f"🧠 Treinando com {len(X_train)} jogos...")
    xgb_params = settings['model']['params']
    model = XGBClassifier(**xgb_params)
    model.fit(X_train, y_train)
    
    # Avaliação
    if len(X_test) > 0:
        y_pred = model.predict(X_test)
        y_probs = model.predict_proba(X_test)[:, 1] # Probabilidade da classe 1 (Vitória)
        
        # Métricas Globais
        global_acc = accuracy_score(y_test, y_pred)
        global_brier = brier_score_loss(y_test, y_probs)
        
        print("-" * 30)
        print(f"📊 ACURÁCIA GLOBAL: {global_acc:.2%}")
        print(f"🎯 BRIER SCORE: {global_brier:.4f} (Quanto menor, melhor)")
        
        # --- CALIBRATION CURVE ---
        print("   📉 Gerando Curva de Calibração...")
        prob_true, prob_pred = calibration_curve(y_test, y_probs, n_bins=10, strategy='uniform')
        
        plt.figure(figsize=(10, 10))
        plt.plot(prob_pred, prob_true, marker='o', label='XGBoost', color='blue')
        plt.plot([0, 1], [0, 1], linestyle='--', label='Perfeitamente Calibrado', color='gray')
        
        plt.xlabel('Probabilidade Predita (Confiança do Modelo)')
        plt.ylabel('Fração de Reais Vitórias')
        plt.title(f'Curva de Calibração (Brier: {global_brier:.4f})')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        output_dir = os.path.join("models", "artifacts")
        os.makedirs(output_dir, exist_ok=True)
        calib_file = os.path.join(output_dir, "calibration_curve.png")
        plt.savefig(calib_file, dpi=300)
        print(f"      -> Salvo em: {calib_file}")

        # Métricas por Role (Mantido)
        metrics_list = []
        run_date = datetime.now()
        
        for role in roles_test.unique():
            mask = (roles_test == role)
            if mask.sum() == 0: continue
            
            y_test_r = y_test[mask]
            y_pred_r = y_pred[mask]
            
            acc = accuracy_score(y_test_r, y_pred_r)
            p, r, f1, _ = precision_recall_fscore_support(y_test_r, y_pred_r, average='binary', zero_division=0)
            
            metrics_list.append({
                'run_date': run_date,
                'role': role,
                'accuracy': round(acc, 4),
                'precision': round(p, 4),
                'recall': round(r, 4),
                'f1_score': round(f1, 4),
                'sample_size': len(y_test_r)
            })
            print(f"      -> {role}: Acc={acc:.1%} | F1={f1:.2f}")

        if metrics_list:
            df_metrics = pd.DataFrame(metrics_list)
            df_metrics.to_sql('dim_model_metrics_by_role', engine, if_exists='append', index=False)

    # Salvar Modelo
    joblib.dump(model, MODEL_FILENAME)

if __name__ == "__main__":
    train_model()