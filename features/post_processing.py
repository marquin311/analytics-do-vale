import pandas as pd
import numpy as np

def calculate_ai_score(df):
    """
    Gera um Score de 0 a 100 HÍBRIDO.
    Separa a performance individual do resultado do jogo.
    Versão: v9.0 (Fair Play Update)
    """
    df = df.copy()
    
    # --- 1. BASE SCORE (MUDANÇA CRÍTICA) ---
    # Começamos com 50 (Neutro). O jogador ganha ou perde pontos a partir daqui.
    # Não dependemos mais 100% da probabilidade de vitória.
    base_score = 50.0 
    
    # O Resultado influencia, mas não define tudo (Peso 20%)
    if 'win_probability' in df.columns:
        # Se prob é 0.9 (Win), ganha +18 pts. Se é 0.1 (Loss), ganha +2 pts.
        base_score += (df['win_probability'] * 20)
    elif 'win' in df.columns:
        # Fallback se não tiver probabilidade
        base_score += np.where(df['win'], 20, 5)

    # --- 2. MÉTRICAS DE IMPACTO (Onde o SVP brilha) ---
    adjustments = pd.Series(0.0, index=df.index)

    # A. Economia (Ouro e XP) - O mais importante
    if 'gold_diff_at_15' in df.columns:
        # Normaliza: 1000 de ouro = +10 pontos. -1000 ouro = -10 pontos.
        # Clip para evitar notas infinitas em stomps (max +/- 15 pts)
        gold_impact = (df['gold_diff_at_15'] / 100).clip(-15, 15)
        adjustments += gold_impact

    # B. KDA / Sobrevivência (Peso Médio)
    if 'kda' in df.columns:
        # KDA > 3 é bom (+), KDA < 2 é ruim (-)
        # Fórmula: (KDA - 3) * 2
        # Ex: KDA 6 = (6-3)*2 = +6 pts
        # Ex: KDA 0.5 = (0.5-3)*2 = -5 pts
        kda_impact = ((df['kda'] - 3) * 2).clip(-10, 10)
        adjustments += kda_impact

    # C. Dano e Participação (Carry)
    if 'dpm' in df.columns:
        # Simplificado: DPM > 500 ganha bônus progressivo
        dpm_bonus = np.where(df['dpm'] > 600, 5.0, 
                             np.where(df['dpm'] > 400, 2.0, -2.0))
        adjustments += dpm_bonus

    # D. Visão (Suporte/Jungle)
    if 'vision_score_per_min' in df.columns:
        vis_bonus = np.where(df['vision_score_per_min'] > 1.5, 5.0, 0.0)
        adjustments += vis_bonus
    # Fallback se não tiver per_min, usa bruto
    elif 'vision_score' in df.columns: 
         adjustments += np.where(df['vision_score'] > 30, 3.0, 0.0)

    # --- 3. PENALIDADES ESTRUTURAIS ---
    # Mortes Excessivas (Feeding Hard)
    if 'deaths' in df.columns:
        # Morrer mais de 7 vezes começa a punir pesado
        death_penalty = np.where(df['deaths'] > 7, (df['deaths'] - 7) * 3, 0)
        adjustments -= death_penalty

    # --- 4. CÁLCULO FINAL ---
    final_score = base_score + adjustments
    
    # Proteção para Vencedores "Mochila" (Win mas jogou mal)
    # Se ganhou, mas o score calculado foi < 40, sobe para 45 (Carregado)
    if 'win' in df.columns:
        mask_carried = (df['win'] == True) & (final_score < 40)
        final_score[mask_carried] = 45

    # Proteção para Perdedores "SVP" (Loss mas jogou muito)
    # Se perdeu, mas score > 80, mantém (é o Ace)
    
    # Clip Final (0-100)
    df['ai_score'] = final_score.clip(0, 100).round(1)

    # Gera Labels e Textos
    df['ai_rank'] = df['ai_score'].apply(get_rank_label)
    df['ai_rating_text'] = df.apply(generate_feedback_text, axis=1)

    return df

def get_rank_label(score):
    if score >= 85: return 'S+' # Ajustado de 90 para 85 ser mais atingível
    if score >= 75: return 'S'
    if score >= 65: return 'A'
    if score >= 55: return 'B'
    if score >= 45: return 'C'
    if score >= 30: return 'D'
    return 'F'

def generate_feedback_text(row):
    score = row.get('ai_score', 50)
    is_win = row.get('win', False)
    
    if score >= 80:
        return "MVP / SVP: Performance de elite."
    elif score >= 65:
        return "Muito bom: Impacto positivo consistente."
    elif score >= 50:
        return "Na média: Cumpriu sua função."
    elif score >= 40:
        if is_win: return "Carregado: Vitória apesar do desempenho."
        else: return "Abaixo da média: Dificuldade na partida."
    else:
        return "Crítico: Precisa rever fundamentos (Farm/Mortes)."