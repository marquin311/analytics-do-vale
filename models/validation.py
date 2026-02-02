import pandas as pd
import joblib
import xgboost as xgb
import matplotlib.pyplot as plt
import os
from sklearn.metrics import brier_score_loss, accuracy_score
from sklearn.model_selection import train_test_split
from database import get_engine
from config import FEATURES_MODEL, MODEL_FILENAME, settings
from features.engine import prepare_data_for_ml

def load_science_data():
    """Carrega dados brutos e aplica feature engineering"""
    engine = get_engine()
    print("🧪 Carregando dados para validação científica...")
    query = "SELECT * FROM fact_match_player_performance WHERE team_position != 'UNKNOWN'"
    # Nota: Simplifiquei a query para o exemplo, use a sua query completa com kills se precisar
    with engine.connect() as conn:
        df_raw = pd.read_sql(query, conn)
    return prepare_data_for_ml(df_raw)

def run_brier_check():
    """Calcula Brier Score por Role"""
    if not os.path.exists(MODEL_FILENAME):
        print("❌ Modelo não encontrado.")
        return

    model = joblib.load(MODEL_FILENAME)
    df = load_science_data()
    
    # Split consistente (mesmo seed do treino)
    split_idx = int(len(df) * 0.8)
    X_test = df[FEATURES_MODEL].iloc[split_idx:]
    y_test = df['win'].astype(int).iloc[split_idx:]
    roles_test = df['team_position'].iloc[split_idx:]
    
    y_probs = model.predict_proba(X_test)[:, 1]
    
    print(f"\n{'ROLE':<10} | {'BRIER':<10} | STATUS")
    print("-" * 35)
    for role in sorted(roles_test.unique()):
        mask = (roles_test == role)
        if mask.sum() == 0: continue
        score = brier_score_loss(y_test[mask], y_probs[mask])
        print(f"{role:<10} | {score:.4f}     | {'💎' if score < 0.1 else '⚠️'}")

def run_ablation_study():
    """Roda o estudo de importância de features"""
    print("✂️ Iniciando Ablation Study...")
    df = load_science_data()
    X = df[FEATURES_MODEL]
    y = df['win'].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Baseline
    params = settings['model']['params']
    base_model = xgb.XGBClassifier(**params)
    base_model.fit(X_train, y_train)
    base_acc = accuracy_score(y_test, base_model.predict(X_test))
    
    print(f"📊 Baseline Acc: {base_acc:.2%}")
    results = []
    
    for feat in FEATURES_MODEL:
        feats_temp = [f for f in FEATURES_MODEL if f != feat]
        model_temp = xgb.XGBClassifier(**params)
        model_temp.fit(X_train[feats_temp], y_train)
        acc = accuracy_score(y_test, model_temp.predict(X_test[feats_temp]))
        delta = acc - base_acc
        print(f"   - {feat}: {delta:+.2%}")
        results.append({'feature': feat, 'delta': delta})
        
    # Plotagem rápida
    if results:
        res_df = pd.DataFrame(results).sort_values('delta')
        plt.figure(figsize=(10, 8))
        plt.barh(res_df['feature'], res_df['delta'], color='salmon')
        plt.title("Ablation Study v8.0")
        os.makedirs("models/artifacts", exist_ok=True)
        plt.savefig("models/artifacts/ablation_new.png")
        print("✅ Gráfico salvo em models/artifacts/ablation_new.png")