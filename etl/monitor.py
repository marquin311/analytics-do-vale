import pandas as pd
from sqlalchemy import text
from database import get_engine
import time
import os

TARGETS = {
    # Américas
    'NA1': 6000, 'BR1': 6000, 'LA1': 1000, 'LA2': 1000,
    
    # Europa & Rússia & Turquia
    'EUW1': 8000, 'EUN1': 2000, 'RU': 500, 'TR1': 1000,
    
    # Ásia & Oceânia
    'KR': 12000, 'OC1': 2000
}

def make_progress_bar(pct, length=15):
    fill_len = min(int(length * pct / 100), length)
    return '█' * fill_len + '░' * (length - fill_len)

def watch_stats():
    """Loop de monitoramento do banco de dados"""
    engine = get_engine()
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            query = "SELECT SPLIT_PART(match_id, '_', 1) as region, COUNT(DISTINCT match_id) as total FROM fact_match_player_performance GROUP BY 1 ORDER BY 2 DESC"
            
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn)
            
            if df.empty:
                print("📭 Banco vazio.")
            else:
                print("="*60)
                print("📊 MONITOR v8.0")
                print("="*60)
                total_global = df['total'].sum()
                
                for _, row in df.iterrows():
                    reg = row['region']
                    curr = row['total']
                    target = TARGETS.get(reg, 0)
                    pct = (curr / target * 100) if target > 0 else 0
                    bar = make_progress_bar(pct)
                    print(f"{reg:<5} | {curr:>5} / {target:<5} | {bar} | {pct:>5.1f}%")
                
                print("-" * 60)
                print(f"GLOBAL: {total_global:,} partidas")
                print("="*60)
            
            print("\n🔄 Ctrl+C para sair. Atualizando em 30s...")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n👋 Monitor encerrado.")