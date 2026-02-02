import sys
import os
import uvicorn
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

sys.path.append(os.getcwd())
from models.coach import LoLCoach
from database import get_engine

app = FastAPI(title="Analytics do Vale API", version="16.7.0") 
coach = LoLCoach()

# --- MODELOS ---
class MatchSummary(BaseModel):
    match_id: str
    champion: str
    role: str
    win: bool
    ai_score: int
    archetype: str
    verdict_short: str
    date: str
    match_tag: str
    extra_context: dict 

class PlayerComparisonStats(BaseModel):
    avg_score_win: float
    avg_score_loss: float
    risk_win: str
    risk_loss: str

class PlayerProfileStats(BaseModel):
    dominant_archetype: str
    avg_score: float
    score_percentile: str
    consistency: str 
    total_games: int
    tags: List[str]
    comparison: PlayerComparisonStats
    analysis_confidence: str 
    narrative_summary: str   

class PlayerHistoryResponse(BaseModel):
    summoner_name: str
    profile: PlayerProfileStats
    matches: List[MatchSummary]

class RankingEntry(BaseModel):
    rank: int
    summoner_name: str
    region: str
    main_role: str
    consistency_label: str
    reliability_label: str
    trend: str
    games_played: int
    win_rate: float
    avg_ai_score: float
    ranking_score: float

class FriendsList(BaseModel):
    summoners: List[str]

# --- ENDPOINTS ---
@app.get("/")
def health_check(): return {"status": "online", "version": "16.7.0"}

@app.get("/player/{region}/{name}/history", response_model=PlayerHistoryResponse)
def get_player_history(region: str, name: str, limit: int = 10):
    engine = get_engine()
    try:
        query_user = f"SELECT DISTINCT puuid, summoner_name FROM fact_match_player_performance WHERE summoner_name ILIKE '{name}' LIMIT 1"
        with engine.connect() as conn: user_df = pd.read_sql(query_user, conn)
        
        if user_df.empty: raise HTTPException(status_code=404, detail="Jogador não encontrado.")
        puuid = user_df.iloc[0]['puuid']
        real_name = user_df.iloc[0]['summoner_name']

        query_match_ids = f"SELECT match_id, game_start_timestamp FROM fact_match_player_performance WHERE puuid = '{puuid}' ORDER BY game_start_timestamp DESC LIMIT 30"
        with engine.connect() as conn: match_ids_df = pd.read_sql(query_match_ids, conn)

        history = []; scores = []; archetypes = []; risks = []; scores_win = []; scores_loss = []; risks_win = []; risks_loss = []

        for idx, row_match in match_ids_df.iterrows():
            m_id = row_match['match_id']
            query_full_match = f"SELECT * FROM fact_match_player_performance WHERE match_id = '{m_id}'"
            with engine.connect() as conn: full_match_df = pd.read_sql(query_full_match, conn)
            
            analysis = coach.analyze_match_context(full_match_df, puuid)
            
            if analysis:
                target_row = full_match_df[full_match_df['puuid'] == puuid].iloc[0]
                
                # Stats Calc
                raw_duration = target_row.get('game_duration_sec', target_row.get('game_duration', 1800))
                duration_min = max(1, raw_duration / 60)
                if 'total_cs' in target_row: total_cs = target_row['total_cs']
                else: total_cs = target_row.get('total_minions_killed', 0) + target_row.get('neutral_minions_killed', 0)
                cs_min_real = round(total_cs / duration_min, 1)

                k = int(target_row.get('kills', 0)); d = int(target_row.get('deaths', 0)); a = int(target_row.get('assists', 0))
                kda_ratio = round((k + a) / max(1, d), 2)
                kda_str = f"{k}/{d}/{a}"
                my_team_id = target_row['team_id']
                team_stats = full_match_df[full_match_df['team_id'] == my_team_id]
                total_team_kills = team_stats['kills'].sum()
                kp_percent = int(((k + a) / max(1, total_team_kills)) * 100)

                sc = analysis['score']
                rk = analysis.get('risk_label', 'Normal') # Fallback seguro
                scores.append(sc); archetypes.append(analysis['archetype_label']); risks.append(rk)
                
                if target_row['win']: scores_win.append(sc); risks_win.append(rk)
                else: scores_loss.append(sc); risks_loss.append(rk)
                
                if idx < limit:
                    history.append({
                        "match_id": m_id,
                        "champion": target_row['champion_name'],
                        "role": target_row['team_position'],
                        "win": bool(target_row['win']),
                        "ai_score": sc,
                        "archetype": analysis['archetype_label'],
                        "verdict_short": analysis['verdict'],
                        "match_tag": analysis['match_tag'],
                        "date": str(row_match['game_start_timestamp']),
                        "extra_context": { 
                            "duration": analysis.get('duration_label', '-'),
                            "type": analysis.get('game_type_label', '-'),
                            "risk": rk,
                            "opportunity": analysis.get('opportunity', {}),
                            "factors": analysis.get('factors', {}),
                            "timeline": analysis['timeline'],
                            "feeding_cause": analysis.get('feeding_cause'),
                            "context": analysis.get('context', {}),
                            "lane_verdict": analysis.get('context', {}).get('lane_verdict', '-'),
                            "win_prob": analysis.get('ai_prediction', 50),
                            "cs_min": cs_min_real,
                            "kda_str": kda_str,
                            "kda_ratio": kda_ratio,
                            "kp": kp_percent
                        }
                    })

        tags = []; comp_stats = PlayerComparisonStats(avg_score_win=0, avg_score_loss=0, risk_win="-", risk_loss="-"); percentile_label = "N/A"
        narrative = "Dados insuficientes."
        confidence_label = "Baixa"

        if scores:
            avg_s = np.mean(scores); std_s = np.std(scores)
            dom_arch = max(set(archetypes), key=archetypes.count) if archetypes else "Flexível"
            if std_s < 10: consist = "🎯 Alta (Robô)"
            elif std_s < 20: consist = "⚖️ Normal"
            else: consist = "🎢 Volátil"

            if avg_s > 80: percentile_label = "Top 5% (Elite)"
            elif avg_s > 70: percentile_label = "Top 20% (Sólido)"
            elif avg_s > 50: percentile_label = "Acima da Média"
            else: percentile_label = "Abaixo da Média"

            high_risk_count = sum(1 for r in risks if "Crítico" in r or "Alta" in r)
            if high_risk_count >= len(risks) * 0.3: tags.append("⚠️ Padrão de Alto Risco")
            if len(scores) >= 3 and np.mean(scores[:3]) < 40: tags.append("❄️ Sequência Fria")
            
            s_win = np.mean(scores_win) if scores_win else 0
            s_loss = np.mean(scores_loss) if scores_loss else 0
            r_win = max(set(risks_win), key=risks_win.count) if risks_win else "-"
            r_loss = max(set(risks_loss), key=risks_loss.count) if risks_loss else "-"
            
            comp_stats = PlayerComparisonStats(avg_score_win=round(float(s_win), 1), avg_score_loss=round(float(s_loss), 1), risk_win=r_win.split(" ")[1] if " " in r_win else r_win, risk_loss=r_loss.split(" ")[1] if " " in r_loss else r_loss)
            
            n_games = len(scores)
            if n_games >= 20: confidence_label = "Alta (Verificada)"
            elif n_games >= 10: confidence_label = "Média"
            
            trend = "estável"
            if len(scores) >= 5:
                recent = np.mean(scores[:5]); old = np.mean(scores[5:]) if len(scores) > 5 else recent
                if recent > old + 5: trend = "em ascensão"
                elif recent < old - 5: trend = "em queda recente"
            narrative = f"Nas últimas {n_games} partidas, seu impacto foi **{trend}**. Seu estilo principal é **{dom_arch}**."

        else:
            avg_s = 0; consist = "-"; dom_arch = "-"; tags = []

        profile = PlayerProfileStats(
            dominant_archetype=dom_arch, avg_score=round(float(avg_s), 1), score_percentile=percentile_label,
            consistency=consist, total_games=len(match_ids_df), tags=tags, comparison=comp_stats,
            analysis_confidence=confidence_label, narrative_summary=narrative
        )

        return {"summoner_name": real_name, "profile": profile, "matches": history}

    except Exception as e: 
        print(f"Erro Fatal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ranking", response_model=List[RankingEntry])
def get_ranking(role: Optional[str] = None):
    engine = get_engine()
    where_clause = f"WHERE UPPER(p.team_position) = '{role.upper()}'" if role and role != "TODOS" else ""
    query = f"""
    SELECT p.summoner_name, COALESCE(p.team_position, 'UNKNOWN') as main_role, COUNT(p.match_id) as games, 
    AVG(CASE WHEN p.win = true THEN 1 ELSE 0 END) as win_rate, AVG(CAST(pred.ai_score AS FLOAT)) as real_avg_score, 
    STDDEV(CAST(p.gold_diff_at_15 AS FLOAT)) as volatility_proxy 
    FROM fact_match_player_performance p
    LEFT JOIN fact_match_predictions pred ON p.match_id = pred.match_id AND p.puuid = pred.puuid
    {where_clause} GROUP BY p.summoner_name, p.team_position HAVING COUNT(p.match_id) >= 1 ORDER BY games DESC LIMIT 200
    """
    try:
        with engine.connect() as conn: df = pd.read_sql(query, conn)
        if df.empty: return []
        ranking_list = []
        for i, row in df.iterrows():
            wr = float(row['win_rate']); games = int(row['games']); volatility = float(row['volatility_proxy']) if pd.notnull(row['volatility_proxy']) else 1000
            db_score = row['real_avg_score']
            ai_score = float(db_score) if pd.notnull(db_score) and db_score > 0 else min(max(70 + (wr * 20), 0), 100)
            final_score = (ai_score * 0.6) + (wr * 100 * 0.3) + (np.log1p(games) * 5)
            if volatility < 800: consist = "🔒 Alta"
            elif volatility < 1500: consist = "⚖️ Média"
            else: consist = "🎲 Volátil"
            if games >= 50: reliab = "🟢 Verificado"
            elif games >= 20: reliab = "🟡 Moderado"
            else: reliab = "🔴 Amostra Baixa"
            if wr >= 0.65: trend = "📈 Subindo"
            elif wr <= 0.45: trend = "📉 Caindo"
            else: trend = "➖ Estável"
            ranking_list.append({"rank": 0,"summoner_name": row['summoner_name'],"region": "KR","main_role": row['main_role'],"consistency_label": consist,"reliability_label": reliab,"trend": trend,"games_played": games,"win_rate": wr,"avg_ai_score": round(ai_score, 1),"ranking_score": round(final_score, 1)})
        ranking_list.sort(key=lambda x: x['ranking_score'], reverse=True)
        for idx, item in enumerate(ranking_list): item['rank'] = idx + 1
        return ranking_list[:50]
    except: return []

@app.post("/ranking/friends", response_model=List[RankingEntry])
def get_custom_ranking(payload: FriendsList):
    """Endpoint dedicado para a Liga Privada (Busca customizada)"""
    engine = get_engine()
    if not payload.summoners: return []
    
    # Sanitiza nomes para SQL e busca independente de maiúscula/minúscula
    names_clean = [n.lower().strip() for n in payload.summoners]
    names_sql = "', '".join(names_clean)
    
    # Query otimizada: Busca APENAS os amigos, sem limite de Top 200
    query = f"""
    SELECT p.summoner_name, COALESCE(p.team_position, 'UNKNOWN') as main_role, COUNT(p.match_id) as games, 
    AVG(CASE WHEN p.win = true THEN 1 ELSE 0 END) as win_rate, AVG(CAST(pred.ai_score AS FLOAT)) as real_avg_score, 
    STDDEV(CAST(p.gold_diff_at_15 AS FLOAT)) as volatility_proxy 
    FROM fact_match_player_performance p
    LEFT JOIN fact_match_predictions pred ON p.match_id = pred.match_id AND p.puuid = pred.puuid
    WHERE LOWER(p.summoner_name) IN ('{names_sql}')
    GROUP BY p.summoner_name, p.team_position 
    HAVING COUNT(p.match_id) >= 1
    """
    
    try:
        with engine.connect() as conn: df = pd.read_sql(query, conn)
        if df.empty: return []
        
        ranking_list = []
        for i, row in df.iterrows():
            # Lógica de Cálculo Idêntica ao Ranking Global
            wr = float(row['win_rate']); games = int(row['games']); volatility = float(row['volatility_proxy']) if pd.notnull(row['volatility_proxy']) else 1000
            db_score = row['real_avg_score']
            ai_score = float(db_score) if pd.notnull(db_score) and db_score > 0 else min(max(70 + (wr * 20), 0), 100)
            final_score = (ai_score * 0.6) + (wr * 100 * 0.3) + (np.log1p(games) * 5)
            
            if volatility < 800: consist = "🔒 Alta"
            elif volatility < 1500: consist = "⚖️ Média"
            else: consist = "🎲 Volátil"
            
            if games >= 50: reliab = "🟢 Verificado"
            elif games >= 20: reliab = "🟡 Moderado"
            else: reliab = "🔴 Amostra Baixa"
            
            if wr >= 0.65: trend = "📈 Subindo"
            elif wr <= 0.45: trend = "📉 Caindo"
            else: trend = "➖ Estável"
            
            ranking_list.append({
                "rank": 0,
                "summoner_name": row['summoner_name'],
                "region": "BR1", # Assumindo BR para lista de amigos
                "main_role": row['main_role'],
                "consistency_label": consist,
                "reliability_label": reliab,
                "trend": trend,
                "games_played": games,
                "win_rate": wr,
                "avg_ai_score": round(ai_score, 1),
                "ranking_score": round(final_score, 1)
            })
            
        ranking_list.sort(key=lambda x: x['ranking_score'], reverse=True)
        for idx, item in enumerate(ranking_list): item['rank'] = idx + 1
        
        return ranking_list
        
    except Exception as e:
        print(f"Erro no ranking amigos: {e}")
        return []

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)