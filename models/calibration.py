import pandas as pd
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import sys
from sklearn.calibration import calibration_curve
from sklearn.model_selection import train_test_split
from sklearn.metrics import brier_score_loss

# Ajuste de path para encontrar módulos locais
sys.path.append(os.getcwd())

from database import get_engine
from config import FEATURES_MODEL, MODEL_FILENAME
from features.engine import prepare_data_for_ml

def generate_calibration_plot():
    print("📉 Gerando Curvas de Calibração por Role...")

    # 1. Carregar Modelo Treinado
    if not os.path.exists(MODEL_FILENAME):
        print(f"❌ Erro: Modelo não encontrado em {MODEL_FILENAME}")
        print("   -> Rode 'python main.py train' primeiro.")
        return

    print(f"   -> Carregando modelo: {MODEL_FILENAME}...")
    model = joblib.load(MODEL_FILENAME)

    # 2. Carregar Dados (Mesma lógica do Treino)
    engine = get_engine()
    print("   -> Baixando dados do SQL...")
    
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
    """
    
    with engine.connect() as conn:
        df_raw = pd.read_sql(query, conn)

    # 3. Engenharia de Features (Fundamental!)
    print("   -> Aplicando Engenharia de Features v8.0...")
    df = prepare_data_for_ml(df_raw)
    
    # 4. Preparar Test Set (Isolar dados que o modelo NUNCA viu)
    # Importante: random_state=42 deve ser igual ao do treino para reproduzir o mesmo split
    X = df[FEATURES_MODEL]
    y = df['win'].astype(int)
    roles = df['team_position'] # Guardamos as roles para agrupar depois

    # Split 80/20
    # Precisamos das roles correspondentes ao X_test, então passamos elas no split
    _, X_test, _, y_test, _, roles_test = train_test_split(
        X, y, roles, test_size=0.2, random_state=42
    )

    print(f"   -> Avaliando em {len(X_test)} exemplos de teste.")

    # 5. Predições
    # Probabilidade da classe 1 (Vitória)
    y_prob = model.predict_proba(X_test)[:, 1]

    # 6. Plotagem
    plt.figure(figsize=(10, 10))
    
    # Linha de Referência (Perfeição)
    plt.plot([0, 1], [0, 1], "k--", label="Perfeitamente Calibrado")

    # Cores para cada lane
    unique_roles = sorted(roles_test.unique())
    palette = sns.color_palette("bright", len(unique_roles))
    
    # Loop por Role
    for i, role in enumerate(unique_roles):
        # Filtra indices dessa role
        mask = (roles_test == role)
        
        if mask.sum() < 50:
            print(f"   ⚠️ Pular {role}: Poucos dados ({mask.sum()})")
            continue

        y_test_role = y_test[mask]
        y_prob_role = y_prob[mask]

        # Calcula Brier Score da Role (Erro quadrático médio)
        brier = brier_score_loss(y_test_role, y_prob_role)

        # Calcula a Curva
        # n_bins=10 significa que vamos agrupar as probs em: 0-10%, 10-20%, etc.
        prob_true, prob_pred = calibration_curve(y_test_role, y_prob_role, n_bins=10)

        # Plota
        plt.plot(prob_pred, prob_true, marker='o', linewidth=2, 
                 label=f"{role} (Brier={brier:.3f})", color=palette[i])

    # Estética
    plt.xlabel("Probabilidade Predita pelo Modelo")
    plt.ylabel("Fração Real de Vitórias")
    plt.title("Curva de Calibração por Posição (v8.0)")
    plt.legend(loc="best")
    plt.grid(True, alpha=0.3)
    
    # Salvar
    output_dir = "models/artifacts"
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, "calibration_by_role.png")
    plt.savefig(save_path, dpi=300)
    plt.close()
    
    print(f"✅ Gráfico salvo com sucesso em: {save_path}")

if __name__ == "__main__":
    generate_calibration_plot()