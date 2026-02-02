import pandas as pd
import numpy as np
import joblib
import sys
import os
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

sys.path.append(os.getcwd())
from database import get_engine
from features.engine import prepare_data_for_ml

# Artefatos v10.1
ARTIFACTS_DIR = 'models/artifacts'
CLUSTERS_FILENAME = f'{ARTIFACTS_DIR}/archetypes_v10.joblib'

def train_archetypes():
    print("🧩 [v10.1] REFINANDO ARQUÉTIPOS (K=4)...")
    
    # 1. Carrega Dados
    engine = get_engine()
    query = "SELECT * FROM fact_match_player_performance WHERE team_position != 'UNKNOWN'"
    with engine.connect() as conn:
        df_raw = pd.read_sql(query, conn)
    
    # 2. Engenharia (com nomes corrigidos via engine.py)
    df = prepare_data_for_ml(df_raw)
    
    # 3. Features de Estilo
    style_features = [
        'dpm', 'damage_self_mitigated', 'vision_score', 
        'gold_earned', 'total_minions_killed', 
        'damage_to_objectives', 'time_ccing_others'
    ]
    
    X = df[style_features].fillna(0)
    
    # Pipeline
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    pca = PCA(n_components=3, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    
    # 4. K-MEANS (K=4 para fundir Utility 0 e 4)
    print("   -> Reduzindo para 4 Clusters Sólidos...")
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_pca)
    
    df['archetype_id'] = clusters
    
    # 5. Naming Dinâmico
    summary = df.groupby('archetype_id')[style_features].mean()
    summary_norm = (summary - summary.min()) / (summary.max() - summary.min())
    
    print("\n🏷️  NOVA IDENTIDADE DOS ARQUÉTIPOS:")
    print("-" * 60)
    
    labels = {}
    for cid, row in summary_norm.iterrows():
        tags = []
        if row['damage_self_mitigated'] > 0.6: tags.append("TANK")
        if row['dpm'] > 0.6: tags.append("CARRY")
        if row['vision_score'] > 0.6: tags.append("SUPPORT")
        if row['damage_to_objectives'] > 0.6: tags.append("SPLIT")
        # Ajuste: Gold muito alto define quem farmou a jungle/lane toda
        if row['gold_earned'] > 0.7: tags.append("RICH")
        
        # Fallback para o grupo fundido
        if not tags: tags.append("UTILITY/BALANCED")
        
        label = " / ".join(tags)
        labels[cid] = label
        
        # Contagem para validar tamanho do cluster
        count = len(df[df['archetype_id'] == cid])
        print(f"   Cluster {cid}: {label:<25} (N={count} jogos)")

    pipeline = {
        'scaler': scaler, 'pca': pca, 'kmeans': kmeans, 'labels': labels
    }
    
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(pipeline, CLUSTERS_FILENAME)
    print(f"\n💾 Pipeline salvo em: {CLUSTERS_FILENAME}")

if __name__ == "__main__":
    train_archetypes()