import pandas as pd
import sys
import os
sys.path.append(os.getcwd())
from database import get_engine

def debug_database():
    print("🕵️‍♂️ INICIANDO DIAGNÓSTICO DO BANCO DE DADOS...")
    engine = get_engine()
    
    with engine.connect() as conn:
        # 1. Contagem Total
        count = pd.read_sql("SELECT COUNT(*) as total FROM fact_match_player_performance", conn).iloc[0]['total']
        print(f"\n📊 Total de Linhas na Tabela: {count}")
        
        if count == 0:
            print("❌ O BANCO ESTÁ VAZIO! Rode o pipeline de ingestão (main.py) primeiro.")
            return

        # 2. Verificando Roles (Posições)
        print("\n🔍 Verificando Roles Disponíveis (team_position):")
        roles = pd.read_sql("SELECT DISTINCT team_position FROM fact_match_player_performance", conn)
        print(roles)
        
        # 3. Verificando Regiões
        print("\n🌍 Verificando Regiões (region):")
        regions = pd.read_sql("SELECT DISTINCT region FROM fact_match_player_performance", conn)
        print(regions)

        # 4. Teste da Query de Ranking (Simplificada)
        print("\n🧪 Testando Agregação de Ranking...")
        try:
            # Tenta uma query super simples para ver se agrupa
            query = """
            SELECT summoner_name, COUNT(*) as games 
            FROM fact_match_player_performance 
            GROUP BY summoner_name 
            ORDER BY games DESC 
            LIMIT 5
            """
            sample = pd.read_sql(query, conn)
            print("✅ Top 5 Jogadores por Volume:")
            print(sample)
        except Exception as e:
            print(f"❌ Erro na Query de Teste: {e}")

if __name__ == "__main__":
    debug_database()