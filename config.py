import yaml
import os

# Caminho absoluto para garantir que o arquivo seja encontrado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'settings.yaml')

def load_config():
    """Lê o arquivo YAML e retorna um dicionário"""
    try:
        # A CORREÇÃO ESTÁ AQUI: encoding='utf-8'
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise Exception(f"❌ Arquivo de configuração não encontrado em: {CONFIG_PATH}")
    except Exception as e:
        raise Exception(f"❌ Erro ao ler settings.yaml: {e}")

# Carrega as configurações assim que o módulo é importado
settings = load_config()

# Atalhos úteis
DB_CONN_STR = settings['database']['url']
API_KEY = settings['riot']['api_key']
MODEL_FILENAME = settings['model']['filename']

# Definição das colunas
FEATURES_MODEL = [
    # --- TIER S: MACRO ---
    'map_presence_efficiency_rel',  # Presença > KDA
    'objective_focus_rel',          # Foco em Torre vs Champions
    'profitable_lead_rel',          # Ouro Convertido em Pressão

    # --- TIER A: EFICIÊNCIA DE COMBATE ---
    'lethality_efficiency_rel',     # Eficiência de Dano (Tank Safe)
    'roam_impact_score_rel',        # Rotação

    # --- TIER B: ESPECIALIZAÇÃO POR ROLE ---
    'lane_pressure_index_rel',      # Mid/Top Control
    'split_push_index_rel',         # Top/Side
    'jungle_richness_score_rel',    # Jungle Pathing
    'vision_denial_rel',            # (Novo) Vision Quality

    # --- TIER C: ESTABILIDADE E FUNDAMENTOS ---
    'cs_at_10_rel',                 # Ainda vital para penalizar outliers
    'xp_diff_at_15',                # Melhor proxy de nível
    'recent_form',                  # Momento do jogador
    'performance_stability'         # Consistência
]