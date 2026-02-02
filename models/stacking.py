import pandas as pd
import joblib
import os
import sys
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import brier_score_loss

sys.path.append(os.getcwd())
from database import get_engine
from features.engine import prepare_data_for_ml
from config import FEATURES_MODEL, MODEL_FILENAME

ARTIFACTS_DIR = 'models/artifacts'
CLUSTERS_FILENAME = f'{ARTIFACTS_DIR}/archetypes_v10.joblib'
STACKING_MODEL_FILENAME = f'{ARTIFACTS_DIR}/calibration_heads_v10.joblib'

def train_calibration_layer():
    print("🧠 [v10.1] CALIBRAÇÃO ESTABILIZADA (K=4)...")
    
    if not os.path.exists(MODEL_FILENAME): return
    base_model = joblib.load(MODEL_FILENAME)
    archetype_pipe = joblib.load(CLUSTERS_FILENAME)

    engine = get_engine()
    query = "SELECT * FROM fact_match_player_performance WHERE team_position != 'UNKNOWN'"
    with engine.connect() as conn:
        df_raw = pd.read_sql(query, conn)

    df = prepare_data_for_ml(df_raw)
    
    # Aplica Arquétipos
    style_features = ['dpm', 'damage_self_mitigated', 'vision_score', 'gold_earned', 'total_minions_killed', 'damage_to_objectives', 'time_ccing_others']
    X_style = df[style_features].fillna(0)
    X_scaled = archetype_pipe['scaler'].transform(X_style)
    X_pca = archetype_pipe['pca'].transform(X_scaled)
    df['archetype_id'] = archetype_pipe['kmeans'].predict(X_pca)
    
    labels_map = archetype_pipe['labels']

    # Predição Base
    X_base = df[FEATURES_MODEL]
    df['xgb_prob'] = base_model.predict_proba(X_base)[:, 1]

    # Features de Calibração
    features_v10 = ['xgb_prob', 'pressure_absorption_rel', 'passivity_index', 'resilience_rel']
    
    archetype_models = {}
    
    print("\n⚔️  DIAGNÓSTICO FINAL (Esperamos pesos < 0.20 para Utility):")
    print(f"{'ID':<3} | {'ESTILO':<20} | {'Brier v10':<8} | {'Pressure Weight'} | {'Status'}")
    print("-" * 80)

    for arch_id in sorted(df['archetype_id'].unique()):
        df_arch = df[df['archetype_id'] == arch_id].copy()
        if len(df_arch) < 100: continue

        X_stack = df_arch[features_v10]
        y = df_arch['win'].astype(int)

        # Regressão Logística com regularização padrão (L2) ajuda a segurar pesos loucos
        X_train, X_test, y_train, y_test = train_test_split(X_stack, y, test_size=0.2, random_state=42)
        meta_model = LogisticRegression(C=1.0) 
        meta_model.fit(X_train, y_train)
        
        probs = meta_model.predict_proba(X_test)[:, 1]
        brier = brier_score_loss(y_test, probs)
        w_pressure = meta_model.coef_[0][1] 
        
        archetype_models[arch_id] = meta_model
        
        # Validação de Estabilidade
        label = labels_map.get(arch_id, "Unknown")
        stability = "✅ OK" if abs(w_pressure) < 0.25 else "⚠️ HIGH"
        # Tanks podem ter peso maior, é natural. Utility não deveria.
        if "TANK" in label and w_pressure > 0: stability = "✅ TANK"
        
        print(f"{arch_id:<3} | {label:<20} | {brier:.4f}   | {w_pressure:+.4f}          | {stability}")

    joblib.dump(archetype_models, STACKING_MODEL_FILENAME)
    print(f"\n💾 Salvo em: {STACKING_MODEL_FILENAME}")

if __name__ == "__main__":
    train_calibration_layer()