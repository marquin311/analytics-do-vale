import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from config import DB_CONN_STR

# Configuração de Logs específica para Banco
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_engine = None

def get_engine():
    """
    Retorna uma engine Singleton com Pool de Conexões robusto.
    Evita recriar conexões a cada chamada.
    """
    global _engine
    
    if _engine is None:
        logger.info("🔌 Criando Pool de Conexões SQL...")
        
        _engine = create_engine(
            DB_CONN_STR,
            # --- MELHORIAS IMPLEMENTADAS ---
            pool_size=10,             # Mantém 10 conexões abertas prontas para uso
            max_overflow=20,          # Em pico, cria mais 20 extras
            pool_timeout=30,          # Espera 30s por uma vaga no pool antes de dar erro
            pool_recycle=1800,        # Renova conexões a cada 30min (evita timeout do servidor)
            pool_pre_ping=True,       # VITAL: Testa se a conexão está viva antes de usar
            echo=False                # Mude para True se quiser ver o SQL cru no terminal
        )
    return _engine

def test_connection():
    """Função utilitária para verificar se o banco está on-line"""
    engine = get_engine()
    retries = 3
    
    for i in range(retries):
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("✅ Conexão com Banco de Dados: OK")
                return True
        except OperationalError:
            if i < retries - 1:
                logger.warning(f"⚠️ Falha na conexão. Tentando novamente ({i+1}/{retries})...")
                time.sleep(2)
            else:
                logger.error("❌ Falha crítica: Banco de Dados inacessível.")
                return False

def reset_predictions_table():
    """(Antigo fix_db.py) Recria a tabela de predições"""
    print("🛠️ Manutenção: Recriando tabela 'fact_match_predictions'...")
    engine = get_engine()
    ddl = """
    DROP TABLE IF EXISTS fact_match_predictions;
    CREATE TABLE fact_match_predictions (
        match_id VARCHAR(50) NOT NULL,
        puuid VARCHAR(100) NOT NULL,
        game_start_timestamp BIGINT NOT NULL,
        team_position VARCHAR(20),
        win_probability FLOAT,
        ai_score FLOAT,
        ai_rank VARCHAR(20),
        ai_rating_text VARCHAR(50),
        ai_score_role_norm FLOAT,
        model_version VARCHAR(10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_match_player PRIMARY KEY (match_id, puuid)
    );
    CREATE INDEX idx_preds_puuid ON fact_match_predictions(puuid);
    CREATE INDEX idx_preds_timestamp ON fact_match_predictions(game_start_timestamp DESC);
    """
    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()
    print("✅ Tabela recriada com sucesso.")