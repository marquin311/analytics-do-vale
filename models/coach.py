import pandas as pd
import numpy as np
import joblib
import sys
import os

sys.path.append(os.getcwd())
from database import get_engine
from features.engine import prepare_data_for_ml
from config import FEATURES_MODEL, MODEL_FILENAME

ARTIFACTS_DIR = 'models/artifacts'
CLUSTERS_FILENAME = f'{ARTIFACTS_DIR}/archetypes_v10.joblib'
CALIBRATION_FILENAME = f'{ARTIFACTS_DIR}/calibration_heads_v10.joblib'

class LoLCoach:
    def __init__(self):
        print("🤖 Iniciando LoL AI Coach (v16.6.1 - Schema Fix)...")
        try:
            self.base_model = joblib.load(MODEL_FILENAME)
            self.archetype_pipe = joblib.load(CLUSTERS_FILENAME)
            self.calibration_heads = joblib.load(CALIBRATION_FILENAME)
            print("   ✅ Motores Carregados.")
        except Exception as e:
            print(f"   ❌ Erro de Inicialização: {e}")
            sys.exit(1)

        self.human_aliases = {
            0: "Controlador de Mapa (Suporte)",
            1: "Facilitador Tático",
            2: "Dominante de Recursos (Carry)",
            3: "Iniciador de Vanguarda (Engage)"
        }

    def _analyze_single_row(self, row):
        X_base = pd.DataFrame([row])[FEATURES_MODEL]
        win_prob = self.base_model.predict_proba(X_base)[0, 1]
        
        style_cols = ['dpm', 'damage_self_mitigated', 'vision_score', 'gold_earned', 'total_minions_killed', 'damage_to_objectives', 'time_ccing_others']
        vals = [row.get(c, 0) for c in style_cols]
        X_style = pd.DataFrame([vals], columns=style_cols)
        X_scaled = self.archetype_pipe['scaler'].transform(X_style)
        X_pca = self.archetype_pipe['pca'].transform(X_scaled)
        ml_arch_id = self.archetype_pipe['kmeans'].predict(X_pca)[0]
        
        if row.get('team_position') == 'BOTTOM': final_arch = 2
        elif row.get('team_position') == 'JUNGLE' and ml_arch_id == 0: final_arch = 3
        else: final_arch = ml_arch_id
        
        return int(win_prob * 100), final_arch

    def _calculate_individual_performance(self, row, cs_min):
        score = 50.0 
        gd15 = row.get('gold_diff_at_15', 0)
        score += np.clip(gd15 / 80, -20, 20)

        role = row.get('team_position', 'UNKNOWN')
        if role != 'UTILITY': 
            if cs_min >= 8.0: score += 10
            elif cs_min >= 7.0: score += 5
            elif cs_min < 5.0: score -= 5
            elif cs_min < 4.0: score -= 10

        kda = row.get('kda', 2.0)
        if kda > 4.0: score += 15
        elif kda > 3.0: score += 8
        elif kda < 1.5: score -= 10
        elif kda < 1.0: score -= 15 

        dpm = row.get('dpm', 0)
        if dpm > 800: score += 10
        elif dpm > 600: score += 5
        
        kp = row.get('kill_participation', 0)
        if kp > 0.6: score += 5
        
        return np.clip(score, 0, 100)

    # --- NOVA LÓGICA DE TEXTO (HIERARQUIA DE VERDADE) ---
    def _generate_narrative_block(self, row, score, rank, lane_verdict, factors):
        is_gap = "Gap" in lane_verdict
        is_feeding = self._is_feeding(row)

        if is_feeding or score < 45:
            title = "🚨 PLANO DE RECUPERAÇÃO"
            if is_feeding: text = "Reduza mortes imediatamente. Jogue sob a torre e evite lutas sem visão clara do jungle inimigo."
            elif is_gap: text = "Perda total de pressão de rota. Foque em absorver recursos defensivamente para não acelerar o jogo inimigo."
            else: text = "Impacto global insuficiente. Falta de presença em lutas e objetivos custou ritmo ao time."
            return title, text

        if score >= 70 and rank <= 4 and not is_gap:
            title = "🚀 ALAVANCA DE IMPACTO"
            if len(factors) > 0: text = f"Você criou vantagem de {factors[0].lower()} e converteu em pressão. Continue forçando essa condição de vitória."
            else: text = "Domínio mecânico e macro. Use sua vantagem para invadir e negar recursos do oponente."
            return title, text

        title = "🧭 FOCO TÁTICO"
        if score >= 55: text = "Boa fase de rotas, mas sem conversão agressiva em pressão lateral ou objetivos neutros."
        else: text = "Execução mecanicamente estável, mas com pouca influência decisiva no resultado final do mapa."
        return title, text

    def _generate_factor_category(self, score):
        if score >= 70: return "🟢 DESTAQUES"
        if score >= 45: return "🟦 EXECUÇÃO NEUTRA"
        return "🔴 DÉFICITS"

    def _extract_honest_factors(self, row, score, cs_min):
        factors = []
        dpm = row.get('dpm', 0)
        kp = row.get('kill_participation', 0)
        gold_diff = row.get('gold_diff_at_15', 0)
        deaths = row.get('deaths', 0)

        if score >= 70:
            if dpm > 700: factors.append("Dano Carry")
            if cs_min > 8.0: factors.append("Farm de Elite")
            if gold_diff > 1000: factors.append("Stomp de Rota")
            if kp > 0.65: factors.append("Onipresença")
            if not factors: factors.append("Consistência Geral") 

        elif score >= 45:
            if cs_min > 6.5: factors.append("Farm Estável")
            elif cs_min < 5.0: factors.append("Farm Baixo")
            if kp > 0.5: factors.append("Boa Participação")
            elif kp < 0.3: factors.append("Isolamento")
            if deaths <= 3: factors.append("Jogo Seguro")
            elif deaths >= 6: factors.append("Exposição Média")

        else:
            if deaths >= 7: factors.append("Excesso de Mortes")
            if cs_min < 5.5: factors.append("Déficit de Ouro/Farm")
            if gold_diff < -1000: factors.append("Gap de Rota")
            if kp < 0.3: factors.append("Nulo no Mapa")
            if not factors: factors.append("Baixo Impacto Geral")

        return factors

    def analyze_match_context(self, df_match, target_puuid):
        match_scores = []
        target_row = None
        opponent_row = None
        
        df_processed = prepare_data_for_ml(df_match)
        raw_duration = df_match.iloc[0].get('game_duration_sec', df_match.iloc[0].get('game_duration', 1800))
        game_min = max(1, raw_duration / 60)

        for idx, row in df_processed.iterrows():
            win_prob_score, arch = self._analyze_single_row(row)
            raw_row = df_match[df_match['puuid'] == row['puuid']].iloc[0]
            
            if 'total_cs' in raw_row: total_cs = raw_row['total_cs']
            else: total_cs = raw_row.get('total_minions_killed', 0) + raw_row.get('neutral_minions_killed', 0)
            if total_cs == 0: total_cs = raw_row.get('total_cs', 0)
            cs_min = round(total_cs / game_min, 1)

            perf_score = self._calculate_individual_performance(row, cs_min)
            final_score = int((perf_score * 0.7) + (win_prob_score * 0.3))
            if row.get('win', False): final_score += 5
            final_score = min(max(final_score, 0), 100)

            player_data = {
                'puuid': str(row['puuid']),
                'score': final_score,
                'model_win_prob': win_prob_score,
                'team_id': int(row.get('team_id')),
                'role': str(row.get('team_position')),
                'row_data': row, 
                'raw_row': raw_row, 
                'cs_min': cs_min
            }
            match_scores.append(player_data)
            if row['puuid'] == target_puuid: target_row = player_data

        if not target_row: return None

        for p in match_scores:
            if p['role'] == target_row['role'] and p['team_id'] != target_row['team_id']:
                opponent_row = p
                break
        
        match_scores.sort(key=lambda x: x['score'], reverse=True)
        rank_in_match = next((i+1 for i, p in enumerate(match_scores) if p['puuid'] == target_puuid), 0)
        
        losing_team = [p for p in match_scores if p['score'] < 45]
        global_narrative = "Partida equilibrada."
        if losing_team:
            roles_failed = [p['role'] for p in losing_team if p['team_id'] == target_row['team_id']]
            if 'BOTTOM' in roles_failed and 'UTILITY' in roles_failed: global_narrative = "Colapso no Bot Side."
            elif 'TOP' in roles_failed and 'JUNGLE' in roles_failed: global_narrative = "Descontrole no Top Side."

        lane_verdict = "Rota equilibrada"
        opp_score = 0; opp_cs = 0.0; opp_kda = "-"; opp_champ = "?"
        if opponent_row:
            opp_score = opponent_row['score']; opp_cs = opponent_row['cs_min']
            k = int(opponent_row['raw_row'].get('kills',0)); d = int(opponent_row['raw_row'].get('deaths',0)); a = int(opponent_row['raw_row'].get('assists',0))
            opp_kda = f"{k}/{d}/{a}"; opp_champ = str(opponent_row['raw_row'].get('champion_name', '?'))
            score_diff = target_row['score'] - opp_score
            if score_diff < -20: lane_verdict = "Derrota de Rota (Gap)"
            elif score_diff > 20: lane_verdict = "Dominação de Rota"

        row = target_row['row_data']; score = target_row['score']; cs_min = target_row['cs_min']
        factors_list = self._extract_honest_factors(row, score, cs_min)
        factors_category = self._generate_factor_category(score)
        opp_title, opp_text = self._generate_narrative_block(row, score, rank_in_match, lane_verdict, factors_list)
        
        _, arch_id = self._analyze_single_row(row)
        archetype_label = self.human_aliases.get(arch_id, "Flexível")
        if self._is_feeding(row): archetype_label += " (Comprometido)"

        # --- RESTAURAÇÃO DAS CHAVES QUE A API EXIGE ---
        duration_label, context_label = self._get_game_context(row)
        risk_label = self._get_risk_rating(row, arch_id)
        # ----------------------------------------------

        return {
            "match_id": df_match.iloc[0]['match_id'],
            "score": score,
            "ai_prediction": target_row['model_win_prob'],
            "archetype_label": archetype_label,
            "verdict": "Impacto " + ("Alto" if score > 70 else "Médio" if score > 45 else "Baixo"),
            "match_tag": self._get_match_tag(row, score, row.get('win', False)),
            "timeline": self._calculate_timeline(row),
            "feeding_cause": self._get_feeding_cause(row),
            
            # Chaves antigas restauradas para compatibilidade
            "duration_label": duration_label,
            "game_type_label": context_label,
            "risk_label": risk_label,
            
            # Contexto Rico
            "context": {
                "rank_in_match": rank_in_match,
                "global_narrative": global_narrative,
                "lane_verdict": lane_verdict,
                "opponent": {
                    "champ": opp_champ,
                    "kda": opp_kda,
                    "cs_min": opp_cs,
                    "score": opp_score
                }
            },
            
            "opportunity": { "title": opp_title, "text": opp_text },
            "factors": { "title": factors_category, "items": factors_list }
        }

    # --- HELPERS RESTAURADOS COM LÓGICA ---
    def _is_feeding(self, row):
        deaths = row.get('deaths', 0)
        minutes = row.get('game_duration_min', 30)
        return deaths >= 7 or (deaths / max(1, minutes/10)) >= 4

    def _sanitize_archetype(self, ml_arch_id, role): return ml_arch_id 
    
    def _get_game_context(self, row):
        minutes = row.get('game_duration_min', 30)
        gold_diff = row.get('gold_diff_at_15', 0)
        duration = "⏱️ Curto" if minutes < 25 else "⏱️ Longo" if minutes > 35 else "⏱️ Médio"
        context = "⚖️ Equilibrado" if abs(gold_diff) < 500 else "🚀 Stomp" if gold_diff > 1500 else "🔥 Difícil"
        return duration, context

    def _get_risk_rating(self, row, arch_id):
        if self._is_feeding(row): return "🔥 Crítico"
        deaths = row.get('deaths', 0)
        if deaths > 5: return "⚠️ Alta"
        if deaths < 2: return "🛡️ Baixa"
        return "✅ Média"
    
    def _calculate_timeline(self, row):
        gd15 = row.get('gold_diff_at_15', 0)
        early = int(min(max(5 + (gd15/200), 1), 10))
        return {"early": early, "mid": 5, "late": 5}

    def _get_match_tag(self, row, score, is_win):
        if self._is_feeding(row): return "📉 Colapso" if not is_win else "🎒 Mochila"
        if score > 80: return "👑 MVP"
        if score > 60: return "🛡️ Sólido"
        return "⚠️ Instável"
    
    def _get_feeding_cause(self, row):
        if self._is_feeding(row): return "Excesso de Mortes"
        return None