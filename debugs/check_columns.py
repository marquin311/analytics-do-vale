import pandas as pd
from database import get_engine

def check_db_columns():
    engine = get_engine()
    print("🔍 Verificando esquema da tabela 'fact_match_player_performance'...")
    
    # Pega apenas 1 linha para ver as colunas
    query = "SELECT * FROM fact_match_player_performance LIMIT 1"
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            
        print(f"\n✅ Colunas encontradas ({len(df.columns)}):")
        print("-" * 50)
        
        # Imprime em ordem alfabética para facilitar
        cols = sorted(df.columns.tolist())
        for c in cols:
            print(f" - {c}")
            
        print("-" * 50)
        
        # Verificação específica dos "problemáticos"
        targets = ['gold', 'minion', 'cc', 'time', 'earned']
        print("\n🕵️ Sugestões de nomes parecidos encontrados:")
        for t in targets:
            matches = [c for c in cols if t in c]
            if matches:
                print(f"   [{t}]: {matches}")

    except Exception as e:
        print(f"❌ Erro ao ler banco: {e}")

if __name__ == "__main__":
    check_db_columns()