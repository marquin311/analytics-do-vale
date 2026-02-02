import argparse
import sys
import os
import time  # <--- IMPORTANTE PARA O SLEEP
import concurrent.futures
import unittest

# --- IMPORTAÇÕES DO PROJETO ---
from etl.riot_collector import RiotETL
from database import reset_predictions_table
from etl.monitor import watch_stats
# from models.validation import run_brier_check, run_ablation_study # Comentado para economizar RAM na VPS se não usar

# --- LISTA DE AMIGOS (SEEDS) ---
FRIENDS_LIST = [
    ("Is it a Crime", "REMA"),
    ("ErichAaron", "BRABO"),
    ("Lexdeath", "DRAKE"),
    ("BilboBcteiro", "ADV1"),
    ("Bodão", "Aguia"),
    ("I MISS HER", "AGUIA"),
    ("Alpha smoker", "CEOS"),
    ("Finest", "aguia")
]

# ==============================================================================
# 1. FUNÇÕES AUXILIARES DE DOWNLOAD (ETL)
# ==============================================================================
def download_and_save_queue(etl, match_queue, label="Geral"):
    print(f"   📦 [{label}] Processando fila de {len(match_queue)} partidas...")
    new_count, skip_count = 0, 0
    queue_list = list(match_queue)
    
    for i, m_id in enumerate(queue_list, 1):
        if i % 10 == 0:
            print(f"      [{label}] {i}/{len(match_queue)} processados...")

        if etl.match_exists(m_id):
            skip_count += 1
            continue
            
        try:
            perf, kills, teams = etl.process_match_full(m_id)
            
            if perf:
                etl.upsert(etl.tbl_perf, perf, ['match_id', 'puuid'])
                etl.upsert(etl.tbl_kills, kills, ['death_id'])
                etl.upsert(etl.tbl_teams, teams, ['match_id', 'team_id'])
                new_count += 1
        except Exception as e:
            print(f"⚠️ Erro ao salvar partida {m_id}: {e}")
            
    print(f"✅ [{label}] Fim! {new_count} salvos, {skip_count} ignorados.")

def process_region_group(targets, group_name):
    """Processa regiões sequencialmente (compartilham Rate Limit)."""
    print(f"\n🚀 [THREAD {group_name}] Iniciando...")
    for target in targets:
        print(f"\n✈️  [{group_name}] VIAJANDO PARA: {target['label']}")
        try:
            etl = RiotETL(region=target['region'], routing=target['routing'])
            
            # A lógica de cascata (Challenger->GM->Master) deve estar dentro do get_top_players
            top_puuids = etl.get_top_players(limit=target['limit'])
            
            match_queue = set()
            print(f"   🎯 [{target['region']}] Coletando histórico de {len(top_puuids)} jogadores...")
            
            for i, puuid in enumerate(top_puuids):
                try:
                    # Busca partidas (Ranked Solo/Duo = 420)
                    matches = etl.get_matches(puuid, count=30, queue_id=420) 
                    match_queue.update(matches)
                    
                    # 🛡️ PROTEÇÃO DE DNS E RATE LIMIT (Essencial para VPS)
                    if i % 5 == 0:
                        time.sleep(0.2) 
                        
                except Exception as e:
                    # print(f"Erro ao buscar jogador: {e}") # Silenciado para não poluir log
                    continue
                
            download_and_save_queue(etl, match_queue, label=target['region'])
            
        except Exception as e:
            print(f"❌ [{group_name}] Erro crítico em {target['region']}: {e}")
    print(f"🏁 [THREAD {group_name}] Concluída.")

# ==============================================================================
# 2. ORQUESTRADORES DE DOWNLOAD
# ==============================================================================
def run_friends():
    print("\n🤝 INICIANDO COLETA: AMIGOS...")
    etl = RiotETL() 
    match_queue = set()
    print("   🔎 Buscando PUUIDs e Partidas...")
    for name, tag in FRIENDS_LIST:
        try:
            puuid = etl.get_puuid(name, tag)
            if puuid:
                for q_id in [420, 440]:
                    matches = etl.get_matches(puuid, count=30, queue_id=q_id)
                    match_queue.update(matches)
        except Exception as e:
            print(f"Erro amigo {name}: {e}")
    download_and_save_queue(etl, match_queue, label="Amigos")

def run_pros_parallel(max_workers=4):
    print(f"\n🌍 INICIANDO COLETA PARALELA ({max_workers} WORKERS)...")
    
    # Configuração Completa de Servidores
    group_americas = [
        {'region': 'na1', 'routing': 'americas', 'label': '🇺🇸 North America', 'limit': 1000},
        {'region': 'br1', 'routing': 'americas', 'label': '🇧🇷 Brasil', 'limit': 1000},
        {'region': 'la1', 'routing': 'americas', 'label': '🌮 LAN (Norte)', 'limit': 500},
        {'region': 'la2', 'routing': 'americas', 'label': '🍖 LAS (Sul)', 'limit': 500}
    ] 
    
    group_europe = [
        {'region': 'euw1', 'routing': 'europe', 'label': '🇪🇺 Europe West', 'limit': 1000},
        {'region': 'eun1', 'routing': 'europe', 'label': '🦄 Europe Nordic', 'limit': 800},
        {'region': 'tr1',  'routing': 'europe', 'label': '🇹🇷 Turkey', 'limit': 500},
        {'region': 'ru',   'routing': 'europe', 'label': '🇷🇺 Russia', 'limit': 300}
    ]   
    
    group_asia = [
        {'region': 'kr', 'routing': 'asia', 'label': '🇰🇷 Korea', 'limit': 2000}
    ]
    
    group_oceania = [
        {'region': 'oc1', 'routing': 'sea', 'label': '🇦🇺 Oceania', 'limit': 300}
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        if group_americas: futures.append(executor.submit(process_region_group, group_americas, "AMERICAS"))
        if group_europe:   futures.append(executor.submit(process_region_group, group_europe, "EUROPE"))
        if group_asia:     futures.append(executor.submit(process_region_group, group_asia, "ASIA"))
        if group_oceania:  futures.append(executor.submit(process_region_group, group_oceania, "OCEANIA"))
        
        concurrent.futures.wait(futures)
        
    print("\n✨ TODAS AS REGIÕES FORAM PROCESSADAS! ✨")

# ==============================================================================
# 3. WRAPPERS DE MODELO
# ==============================================================================
def run_train():
    from models.trainer import train_model
    train_model()

def run_predict():
    from models.predictor import run_predictions
    run_predictions()

def run_explain():
    from models.explainability import explain_model
    explain_model()

# ==============================================================================
# 4. ENTRY POINT (CLI)
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoL Analytics v8.1 - Central de Comando")
    subparsers = parser.add_subparsers(dest='command', help='Comando a executar')

    # --- Grupo: Download & Dados ---
    subparsers.add_parser('friends', help='Baixa jogos de amigos')
    
    # Pros com argumento de workers
    pros_parser = subparsers.add_parser('pros', help='Baixa jogos High Elo')
    pros_parser.add_argument('--workers', type=int, default=4, help='Número de threads paralelas (Def: 4)')
    
    subparsers.add_parser('monitor', help='Painel em tempo real do download')
    subparsers.add_parser('init-db', help='[PERIGO] Reseta tabela de predições')
    
    # --- Grupo: Machine Learning ---
    subparsers.add_parser('train', help='Treina o modelo XGBoost')
    subparsers.add_parser('predict', help='Roda predições em novos jogos')
    subparsers.add_parser('explain', help='Gera gráficos SHAP')
    
    # --- Grupo: Ciência & Validação ---
    subparsers.add_parser('evaluate', help='Calcula Brier Score por Role')
    subparsers.add_parser('ablation', help='Roda estudo de feature importance')
    subparsers.add_parser('test', help='Roda testes unitários')

    args = parser.parse_args()

    # Roteamento de Comandos
    if args.command == 'friends':
        run_friends()
    elif args.command == 'pros':
        # Passa o número de workers escolhido (Crucial para VPS com pouca RAM)
        run_pros_parallel(max_workers=args.workers)
    elif args.command == 'monitor':
        watch_stats()
    elif args.command == 'init-db':
        confirm = input("⚠️  ISSO VAI APAGAR O HISTÓRICO DE PREDIÇÕES. Confirmar? (s/n): ")
        if confirm.lower() == 's':
            reset_predictions_table()
    elif args.command == 'train':
        run_train()
    elif args.command == 'predict':
        run_predict()
    elif args.command == 'explain':
        run_explain()
    elif args.command == 'evaluate':
        from models.validation import run_brier_check # Import tardio
        run_brier_check()
    elif args.command == 'ablation':
        from models.validation import run_ablation_study # Import tardio
        run_ablation_study()
    elif args.command == 'test':
        print("🧪 Rodando Testes Unitários...")
        os.system("python -m unittest discover tests")
    else:
        parser.print_help()