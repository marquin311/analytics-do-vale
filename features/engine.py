import pandas as pd
import numpy as np
from config import settings

def calculate_zscore_by_group(df: pd.DataFrame, target_col: str, group_col: str, epsilon: float = 0.001) -> pd.Series:
    if target_col not in df.columns: return pd.Series(0.0, index=df.index)
    
    def z_score_func(x):
        std = x.std()
        safe_std = max(std, epsilon)
        return (x - x.mean()) / safe_std
        
    return df.groupby(group_col)[target_col].transform(z_score_func).fillna(0.0)

def calculate_rolling_stat(df, target_col, group_col, window, min_periods, stat_type='mean'):
    if target_col not in df.columns: return pd.Series(0.0, index=df.index)
    grouped = df.groupby(group_col)[target_col]
    if stat_type == 'mean': return grouped.transform(lambda x: x.rolling(window, min_periods).mean()).fillna(0.0)
    elif stat_type == 'std': return grouped.transform(lambda x: x.rolling(window, min_periods).std()).fillna(0.0)
    return pd.Series(0.0, index=df.index)

def apply_v9_context_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    [FASE 2] Cria as features de 'Inteligência Invisível' para o Estágio 2 de Calibração.
    """
    
    # A. PRESSURE ABSORPTION INDEX
    if 'damage_self_mitigated' in df.columns and 'total_damage_taken' in df.columns:
        df['raw_pressure'] = (df['damage_self_mitigated'] + df['total_damage_taken']) / (df['deaths'] + 1)
        df['pressure_absorption_rel'] = calculate_zscore_by_group(df, 'raw_pressure', 'team_position')
    else:
        df['pressure_absorption_rel'] = 0.0

    # B. PASSIVE KDA INDEX
    if 'dpm' in df.columns and 'kda' in df.columns:
        df['dpm_rel'] = calculate_zscore_by_group(df, 'dpm', 'team_position')
        df['passivity_index'] = (df['kda'] / 3.0) - (df['dpm_rel'])
        df['passivity_index'] = df['passivity_index'].clip(lower=0)
    else:
        df['passivity_index'] = 0.0

    # C. RESILIENCE SCORE (Resourcefulness)
    # Nota: Agora usamos 'gold_earned' (que foi renomeado no prepare_data)
    if 'gold_earned' in df.columns:
        df['resourcefulness'] = df['gold_earned'] / (df['kills'] + 1)
        df['resilience_rel'] = calculate_zscore_by_group(df, 'resourcefulness', 'team_position')
    else:
        df['resilience_rel'] = 0.0

    return df

def prepare_data_for_ml(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # --- 0. PADRONIZAÇÃO DE NOMES (CORREÇÃO DE ESQUEMA DB) ---
    # Mapeia nomes do Banco de Dados -> Nomes Esperados pelo Modelo
    rename_map = {
        'total_gold_earned': 'gold_earned',
        'total_cs': 'total_minions_killed',
        'time_cc_others': 'time_ccing_others'
    }
    df = df.rename(columns=rename_map)
    # ---------------------------------------------------------

    WINDOW = settings['features']['rolling_window']
    MIN_PER = settings['features']['min_periods']
    EPSILON = settings['features']['z_score_epsilon']

    # 1. Tratamento de Nulos
    cols_fix = [
        'gold_velocity', 'damage_to_objectives', 'turret_plates_taken', 
        'cs_at_10', 'gold_at_10', 'solo_kills_at_10', 'invade_kills', 
        'xp_diff_at_15', 'wards_killed_at_10', 'neutral_minions_killed',
        'gold_gain_10_20', 'xp_gain_10_20', 'vision_wards_bought',
        'gold_diff_at_10', 'xp_diff_at_10', 'gold_diff_at_15',
        'cs_diff_at_10', 'cs_diff_at_15', 'vision_score', 'total_damage_dealt',
        'kills', 'assists', 'deaths', 'damage_self_mitigated', 'total_damage_taken', 'gold_earned'
    ]
    for col in cols_fix:
        if col in df.columns: df[col] = df[col].fillna(0)

    # Ordenação Temporal
    if 'game_start_timestamp' in df.columns: 
        df = df.sort_values(['puuid', 'game_start_timestamp'])
    
    # Duração
    if 'game_duration' in df.columns: 
        df['game_duration_min'] = df['game_duration'] / 60
    elif 'game_duration_sec' in df.columns: # Fallback para o nome do banco
        df['game_duration_min'] = df['game_duration_sec'] / 60
    else:
        df['game_duration_min'] = 30

    # --- CÁLCULOS BÁSICOS ---
    df['kda'] = (df['kills'] + df['assists']) / (df['deaths'].replace(0, 1))
    df['dpm'] = df['total_damage_dealt'] / (df['game_duration_min'] + 0.1)

    # =========================================================================
    # 🧬 FEATURES DO MODELO
    # =========================================================================

    # 1. OBJECTIVE FOCUS RATIO 
    df['objective_focus_ratio'] = (df['damage_to_objectives'] + 1) / (df['total_damage_dealt'] + 1)
    df['objective_focus_rel'] = calculate_zscore_by_group(df, 'objective_focus_ratio', 'team_position')

    # 2. LETHALITY EFFICIENCY 
    df['lethality_raw'] = df['total_damage_dealt'] / (df['kills'] + df['assists'] + 1)
    df['lethality_efficiency_rel'] = calculate_zscore_by_group(df, 'lethality_raw', 'team_position') * -1

    # 3. PROFITABLE LEAD 
    df['profitable_lead_score'] = df['gold_diff_at_15'].clip(lower=0) * np.log1p(df['damage_to_objectives'])
    df['profitable_lead_rel'] = calculate_zscore_by_group(df, 'profitable_lead_score', 'team_position')

    # 4. VISION DENIAL RATIO
    df['vision_denial_ratio'] = df['wards_killed_at_10'] / (df['vision_score'] + 1)
    df['vision_denial_rel'] = calculate_zscore_by_group(df, 'vision_denial_ratio', 'team_position')

    # Lane Pressure
    df['lane_pressure_index'] = (df['xp_diff_at_15'] * 0.5) + (df['gold_diff_at_15'] * 0.3) + (df['turret_plates_taken'] * 200)
    df['lane_pressure_index'] = df['lane_pressure_index'].clip(-3000, 3000)
    df['lane_pressure_index_rel'] = calculate_zscore_by_group(df, 'lane_pressure_index', 'team_position')

    # Roam Impact
    assists_early = df.get('assists_at_15', df['assists'] * 0.3)
    invade = df.get('invade_kills', 0)
    df['roam_impact_score'] = (invade * 100) + (assists_early * 50)
    cs_penalty = np.where(df['cs_diff_at_15'] < -20, abs(df['cs_diff_at_15']), 0)
    df['roam_impact_score'] -= (cs_penalty * 2)
    df['roam_impact_score_rel'] = calculate_zscore_by_group(df, 'roam_impact_score', 'team_position')

    # Jungle Richness
    df['jungle_richness_score'] = np.where(
        df['team_position'] == 'JUNGLE',
        df['neutral_minions_killed'] / (df['game_duration_min'] + 1),
        0
    )
    df['jungle_richness_score_rel'] = calculate_zscore_by_group(df, 'jungle_richness_score', 'team_position')
    
    # Split Push Index
    df['raw_kp_score'] = (df['kills'] + df['assists']).clip(lower=0)
    df['split_push_index'] = np.log1p(df['damage_to_objectives']) / (df['raw_kp_score'] + 1)
    df['split_push_index_rel'] = calculate_zscore_by_group(df, 'split_push_index', 'team_position')

    # Map Presence
    df['map_presence_efficiency'] = ((df['kills'] + df['assists']) / (df['total_time_spent_dead'] + 60))
    df['map_presence_efficiency_rel'] = calculate_zscore_by_group(df, 'map_presence_efficiency', 'team_position')

    # Features de Forma
    df['recent_form'] = calculate_rolling_stat(df, 'gold_velocity', 'puuid', WINDOW, MIN_PER, 'mean')
    df['performance_stability'] = 1 / (1 + calculate_rolling_stat(df, 'gold_velocity', 'puuid', WINDOW, MIN_PER, 'std'))

    # Métricas Base
    metrics_norm = ['cs_at_10', 'gold_at_10', 'xp_diff_at_15']
    for col in metrics_norm:
        if col in df.columns:
            df[f'{col}_rel'] = calculate_zscore_by_group(df, col, 'team_position', EPSILON)

    # Aplica Fase 2 (v9)
    df = apply_v9_context_features(df)

    return df