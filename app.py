import streamlit as st
import pandas as pd
import requests
import textwrap

st.set_page_config(page_title="Analytics do Vale", page_icon="🏔️", layout="wide")
API_URL = "http://localhost:8000"

st.markdown("""
<style>
    .score-high { color: #3b82f6; font-weight: 800; }
    .score-mid { color: #60a5fa; font-weight: 700; }
    .score-low { color: #94a3b8; font-weight: 600; }
    
    .match-card-container { background-color: #1e293b; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); overflow: hidden; }
    
    /* Header (Topo do Card) */
    .match-card-header { padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-left: 6px solid #334155; background: linear-gradient(90deg, rgba(30, 41, 59, 0.5) 0%, rgba(30, 41, 59, 0) 100%); }
    .match-win { border-left-color: #3b82f6; } 
    .match-loss { border-left-color: #64748b; }
    
    /* Barra de Stats (Base do Card) */
    .match-stats-row { padding: 10px 20px; background-color: #0f172a; border-top: 1px solid #334155; display: flex; gap: 15px; font-size: 0.85rem; color: #cbd5e1; align-items: center; }
    
    .stat-pill { background: rgba(255, 255, 255, 0.05); padding: 4px 10px; border-radius: 6px; border: 1px solid #334155; display: flex; align-items: center; gap: 6px; }
    .stat-label-mini { color: #94a3b8; font-size: 0.7rem; text-transform: uppercase; font-weight: 600; }
    .stat-val { font-weight: 700; color: #f1f5f9; }
    
    .impact-rank { font-weight: bold; font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; margin-right: 8px; }
    .rank-1 { background: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }
    .rank-10 { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .rank-mid { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
    
    .rivalry-box { background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #334155; margin-top: 10px; }
    .rival-row { display: flex; justify-content: space-between; font-size: 0.9rem; border-bottom: 1px solid #1e293b; padding: 6px 0; }
    .global-narrative { background: #1e1b4b; color: #a5b4fc; padding: 10px 15px; border-radius: 6px; font-size: 0.9rem; margin-bottom: 15px; border-left: 4px solid #6366f1; }
    
    .profile-box { background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 15px; margin-bottom: 25px; }
    .stat-main-label { color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-main-value { color: #f8fafc; font-size: 1.6rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

if 'target_summoner' not in st.session_state: st.session_state.target_summoner = None
if 'active_match_id' not in st.session_state: st.session_state.active_match_id = None

def get_history(name, region="KR"):
    try: return requests.get(f"{API_URL}/player/{region}/{name}/history").json()
    except: return None

def get_ranking(role="TODOS"):
    try: return requests.get(f"{API_URL}/ranking", params={"role": role}).json()
    except: return []

def render_intensity_dots(level): return "●" * level + "○" * (3 - level)

with st.sidebar:
    st.title("🏔️ Analytics do Vale")
    st.caption("v16.7 • Unified Card")
    nav_options = ["🏆 Ranking Global", "🔍 Análise de Jogador"]
    page = st.radio("Navegação", nav_options, index=1 if st.session_state.target_summoner else 0)

if page == "🏆 Ranking Global":
    st.title("🏆 Leaderboard")
    col_filter, _ = st.columns([1, 3])
    with col_filter: role_filter = st.selectbox("Filtrar por Role", ["TODOS", "TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"])
    ranking_data = get_ranking(role_filter)
    if ranking_data:
        df = pd.DataFrame(ranking_data)
        st.dataframe(df[['rank', 'summoner_name', 'main_role', 'avg_ai_score', 'trend', 'win_rate']], hide_index=True, use_container_width=True)
    else: st.warning("Ranking vazio.")

elif page == "🔍 Análise de Jogador":
    st.title("🔍 Análise Profunda")
    c1, c2 = st.columns([3, 1])
    with c1: search_name = st.text_input("Riot ID", value=st.session_state.target_summoner or "", placeholder="Ex: T1 Faker")
    with c2: 
        if st.button("Buscar", type="primary", use_container_width=True): st.session_state.target_summoner = search_name; st.session_state.active_match_id = None; st.rerun()

    if search_name:
        with st.spinner("Analisando Performance..."):
            data = get_history(search_name)
            if not data or "matches" not in data: st.error("Erro ao buscar dados.")
            else:
                prof = data.get('profile', {})
                comp = prof.get('comparison', {})
                
                # --- PERFIL HEADER ---
                st.html(f"""
                <div class="profile-box">
                    <div style="display: flex; justify-content: space-around; width: 100%;">
                        <div style="text-align:center;">
                            <div class="stat-main-label">Score Médio</div>
                            <div class="stat-main-value" style="color: #3b82f6;">{prof.get('avg_score', '-')}</div>
                            <div style="font-size:0.8rem; color:#94a3b8;">{prof.get('score_percentile', '')}</div>
                        </div>
                        <div style="text-align:center;">
                            <div class="stat-main-label">Consistência</div>
                            <div class="stat-main-value">{prof.get('consistency', '-')}</div>
                            <div style="font-size:0.8rem; color:#94a3b8;">Estabilidade</div>
                        </div>
                        <div style="text-align:center; border-left:1px solid #334155; padding-left:20px;">
                            <div class="stat-main-label">Em Vitórias</div>
                            <div style="color:#10b981; font-weight:bold; font-size:1.2rem;">{comp.get('avg_score_win')}</div>
                        </div>
                         <div style="text-align:center;">
                            <div class="stat-main-label">Em Derrotas</div>
                            <div style="color:#ef4444; font-weight:bold; font-size:1.2rem;">{comp.get('avg_score_loss')}</div>
                        </div>
                    </div>
                    <div style="text-align:center; font-style:italic; color:#cbd5e1; font-size:0.9rem; margin-top:10px;">"{prof.get('narrative_summary', '')}"</div>
                </div>
                """)

                st.subheader("Histórico")
                for match in data['matches']:
                    is_win = match['win']
                    css = "match-win" if is_win else "match-loss"
                    score_cls = "score-high" if match['ai_score'] >= 80 else "score-mid" if match['ai_score'] >= 65 else "score-low"
                    
                    ctx = match.get('extra_context', {})
                    match_ctx = ctx.get('context', {})
                    opp_data = ctx.get('opportunity', {})
                    factors_data = ctx.get('factors', {})
                    
                    # 1. Rank Badge
                    rank_in_match = match_ctx.get('rank_in_match', 0)
                    rank_cls = "rank-1" if rank_in_match == 1 else "rank-10" if rank_in_match == 10 else "rank-mid"
                    rank_html = f'<span class="impact-rank {rank_cls}">#{rank_in_match}</span>'
                    
                    # 2. Win Probability Logic
                    win_prob = ctx.get('win_prob', 50)
                    if win_prob >= 70: prob_color = "#3b82f6" 
                    elif win_prob <= 30: prob_color = "#ef4444" 
                    else: prob_color = "#64748b" 
                    
                    if is_win and win_prob < 40: prob_text = "🔥 CLUTCH"
                    elif not is_win and win_prob > 70: prob_text = "💀 THROW"
                    else: prob_text = "Previsão IA"

                    # 3. Card Unificado
                    with st.container():
                        st.html(textwrap.dedent(f"""
                        <div class="match-card-container">
                            <div class="match-card-header {css}">
                                <div style="display:flex; align-items:center;">
                                    <div>
                                        <div style="margin-bottom:4px; font-size:1.1rem; color:#f1f5f9;">
                                            {rank_html} <span style="font-weight:700;">{match['champion']}</span>
                                        </div>
                                        <div style="color:#94a3b8; font-size:0.8rem; margin-left:2px;">
                                            {match['role']} • {match['verdict_short']}
                                        </div>
                                    </div>
                                </div>
                                <div style="text-align:right;">
                                    <div class="{score_cls}" style="font-size:1.6rem; line-height:1;">{match['ai_score']}</div>
                                    <div style="font-size:0.65rem; color:#94a3b8; margin-top:2px;">SCORE</div>
                                </div>
                            </div>
                            
                            <div class="match-stats-row">
                                <div class="stat-pill">
                                    <span class="stat-label-mini">KDA</span> 
                                    <span class="stat-val">{ctx.get('kda_str')}</span>
                                </div>
                                <div class="stat-pill">
                                    <span class="stat-label-mini">KP</span> 
                                    <span class="stat-val">{ctx.get('kp')}%</span>
                                </div>
                                <div class="stat-pill">
                                    <span class="stat-label-mini">CS/M</span> 
                                    <span class="stat-val">{ctx.get('cs_min')}</span>
                                </div>
                                
                                <div style="flex-grow:1; text-align:right; border-left:1px solid #334155; padding-left:15px; margin-left:5px;">
                                    <div style="font-size:0.7rem; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:3px;">
                                        <span style="font-weight:600;">{prob_text}</span>
                                        <span>{win_prob}%</span>
                                    </div>
                                    <div style="width:100%; height:4px; background:#1e293b; border-radius:2px;">
                                        <div style="width:{win_prob}%; height:100%; background:{prob_color}; border-radius:2px;"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """).strip())
                        
                        # --- EXPANSÃO (ANÁLISE DETALHADA) ---
                        is_expanded = (st.session_state.active_match_id == match['match_id'])
                        with st.expander("🔎 Ver Diagnóstico Completo", expanded=is_expanded):
                            if match_ctx.get('global_narrative'):
                                st.html(f'<div class="global-narrative">🤖 <b>Contexto:</b> {match_ctx["global_narrative"]}</div>')
                            
                            c1, c2, c3 = st.columns([1.3, 1.3, 1])
                            
                            with c1: # Coluna 1: Oportunidade e Rival
                                title = opp_data.get('title', 'ANÁLISE')
                                text = opp_data.get('text', '')
                                if "ALAVANCA" in title: st.info(f"**{title}**\n\n{text}")
                                elif "RECUPERAÇÃO" in title: st.error(f"**{title}**\n\n{text}")
                                else: st.warning(f"**{title}**\n\n{text}")

                                opp = match_ctx.get('opponent', {})
                                if opp.get('champ') != '?':
                                    st.html(f"""
                                    <div class="rivalry-box">
                                        <div style="text-align:center; font-size:0.75rem; color:#94a3b8; margin-bottom:8px; text-transform:uppercase;">DUELO vs {opp.get('champ')}</div>
                                        <div class="rival-row"><span>Score</span> <span style="font-weight:bold; color:white;">{match['ai_score']} vs {opp.get('score')}</span></div>
                                        <div class="rival-row"><span>CS/min</span> <span>{ctx.get('cs_min')} vs {opp.get('cs_min')}</span></div>
                                        <div style="text-align:center; font-size:0.8rem; margin-top:8px; color:#cbd5e1; font-style:italic;">{match_ctx.get('lane_verdict', '')}</div>
                                    </div>
                                    """)

                            with c2: # Coluna 2: Fatores
                                f_title = factors_data.get('title', 'FATORES')
                                f_items = factors_data.get('items', [])
                                st.caption(f"**{f_title}**")
                                for item in f_items: st.write(f"• {item}")
                                    
                            with c3: # Coluna 3: Estilo
                                st.caption("**ESTILO JOGADO**")
                                st.write(f"{match['archetype']}")
                            
                            if not is_expanded:
                                if st.button("📌 Fixar", key=f"btn_{match['match_id']}"):
                                    st.session_state.active_match_id = match['match_id']; st.rerun()