import requests
import pandas as pd
import time
import logging
from sqlalchemy import MetaData, Table, text
from sqlalchemy.dialects.postgresql import insert
from database import get_engine
from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RiotETL:
    # 1. ATUALIZAÇÃO: Aceita region/routing como argumentos opcionais
    def __init__(self, region=None, routing=None):
        # Se não passar nada, usa o do settings.yaml (padrão BR)
        # Se passar, usa o argumento (ex: KR/Asia)
        self.api_key = settings['riot']['api_key']
        
        cfg_routing = routing if routing else settings['riot']['routing']
        cfg_region = region if region else settings['riot']['region']
        
        self.routing_url = f"https://{cfg_routing}.api.riotgames.com"
        self.region_url = f"https://{cfg_region}.api.riotgames.com"
        
        self.headers = {"X-Riot-Token": self.api_key}
        self.engine = get_engine()
        self.metadata = MetaData()
        
        try:
            self.tbl_perf = Table('fact_match_player_performance', self.metadata, autoload_with=self.engine)
            self.tbl_kills = Table('fact_kill_events', self.metadata, autoload_with=self.engine)
            self.tbl_teams = Table('fact_match_teams', self.metadata, autoload_with=self.engine)
        except Exception as e:
            logger.error(f"Erro ao carregar tabelas do DB: {e}")

    def _request(self, url):
        time.sleep(1.3) 
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200: return resp.json()
            elif resp.status_code == 403:
                logger.critical("🚨 ERRO 403: API Key Expirada!")
                return None
            elif resp.status_code == 429:
                wait = int(resp.headers.get('Retry-After', 10)) + 2
                logger.warning(f"⏳ Rate Limit (429). Aguardando {wait}s...")
                time.sleep(wait)
                return self._request(url)
            elif resp.status_code == 404: return None
            return None
        except Exception as e:
            logger.error(f"Erro Conexão: {e}")
            return None

    # --- NOVO MÉTODO: BUSCAR DESAFIANTES ---
    def get_top_players(self, limit=300):
        """
        Busca jogadores em cascata (Waterfall) para garantir o limite:
        1. Tenta Challenger
        2. Se não encher, completa com Grandmaster
        3. Se não encher, completa com Master
        """
        collected_entries = []
        
        # Lista de Tiers para iterar
        tiers = [
            ('Challenger', f"{self.region_url}/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"),
            ('Grandmaster', f"{self.region_url}/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5"),
            ('Master', f"{self.region_url}/lol/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5")
        ]

        logger.info(f"🔎 Iniciando busca em cascata para {limit} jogadores...")

        for tier_name, url in tiers:
            if len(collected_entries) >= limit:
                break
            
            remaining = limit - len(collected_entries)
            logger.info(f"   -> Buscando em {tier_name} (Faltam {remaining})...")
            
            data = self._request(url)
            if not data or 'entries' not in data:
                logger.warning(f"      ⚠️ Falha ou lista vazia para {tier_name}.")
                continue
                
            # Ordena por LP (League Points) Do maior para o menor
            # Isso garante que pegamos os "quase-Challengers" do GM
            entries = sorted(data['entries'], key=lambda x: x['leaguePoints'], reverse=True)
            
            # Pega apenas o necessário para completar o limite
            needed_entries = entries[:remaining]
            collected_entries.extend(needed_entries)
            logger.info(f"      ✅ Adicionados {len(needed_entries)} de {tier_name}.")

        # --- CONVERSÃO PARA PUUID ---
        puuids = []
        logger.info(f"🔄 Convertendo {len(collected_entries)} SummonerIDs para PUUIDs...")
        
        for i, entry in enumerate(collected_entries):
            # 1. TENTA PUUID DIRETO (Futuro da API)
            if 'puuid' in entry:
                puuids.append(entry['puuid'])
                continue

            # 2. CONVERTE SUMMONER ID
            sum_id = entry.get('summonerId')
            if not sum_id: continue

            acc_url = f"{self.region_url}/lol/summoner/v4/summoners/{sum_id}"
            acc_data = self._request(acc_url)
            
            if acc_data and 'puuid' in acc_data:
                puuids.append(acc_data['puuid'])
                # Log de progresso a cada 20 para não poluir
                if (i+1) % 20 == 0: 
                    logger.info(f"   ... {i+1}/{len(collected_entries)} convertidos.")
            else:
                logger.warning(f"   ⚠️ Falha ID: {sum_id}")
                
        return puuids

    def match_exists(self, match_id):
        """Verifica se a partida já existe no banco"""
        try:
            with self.engine.connect() as conn:
                query = text("SELECT 1 FROM fact_match_player_performance WHERE match_id = :mid LIMIT 1")
                result = conn.execute(query, {"mid": match_id}).fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Erro check match: {e}")
            return False

    def get_puuid(self, name, tag):
        # Codificação correta da URL para Riot ID
        url = f"{self.routing_url}/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        data = self._request(url)
        return data['puuid'] if data else None

    def get_matches(self, puuid, count=20, queue_id=None):
        # Base da URL
        url = f"{self.routing_url}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}"
        
        # Se especificou uma fila (Ex: 420 ou 440), adiciona o filtro
        if queue_id:
            url += f"&queue={queue_id}"
            
        data = self._request(url)
        return data if data else []

    def get_champion_mastery(self, puuid, champion_id):
        url = f"{self.region_url}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champion_id}"
        data = self._request(url)
        return data.get('championPoints', 0) if data else 0

    # --- LÓGICA DE EXTRAÇÃO (MÉTODOS PRIVADOS) ---
    def _extract_timeline_snapshot(self, timeline_data, minute):
        stats = {i: {'cs':0, 'jungle_cs':0, 'lane_cs':0, 'gold_total':0, 'xp':0, 'k':0, 'd':0, 'a':0, 'solo_k':0, 'plates':0, 'wards_placed':0, 'control_wards_placed':0, 'wards_killed':0, 'level':1, 'gold_current':0} for i in range(1, 11)}
        if not timeline_data: return stats
        frames = timeline_data['info']['frames']
        target_idx = minute if len(frames) > minute else len(frames)-1
        limit_ms = minute * 60000
        
        for pid_str, p in frames[target_idx]['participantFrames'].items():
            pid = int(pid_str)
            stats[pid].update({
                'cs': p['minionsKilled'] + p['jungleMinionsKilled'],
                'jungle_cs': p['jungleMinionsKilled'], 'lane_cs': p['minionsKilled'],
                'gold_total': p['totalGold'], 'gold_current': p['currentGold'], 'xp': p['xp'], 'level': p['level']
            })
        for frame in frames:
            for ev in frame['events']:
                if ev['timestamp'] > limit_ms: break
                if ev['type'] == 'CHAMPION_KILL':
                    k, v = ev.get('killerId', 0), ev.get('victimId', 0)
                    assts = ev.get('assistingParticipantIds', [])
                    if k>0: 
                        stats[k]['k']+=1
                        if not assts: stats[k]['solo_k']+=1
                    if v>0: stats[v]['d']+=1
                    for a in assts: 
                        if a>0: stats[a]['a']+=1
                elif ev['type'] == 'TURRET_PLATE_DESTROYED':
                    if ev.get('killerId', 0) > 0: stats[ev['killerId']]['plates']+=1
                elif ev['type'] == 'WARD_PLACED':
                    creator = ev.get('creatorId', 0)
                    if creator > 0:
                        stats[creator]['wards_placed']+=1
                        if ev.get('wardType') == 'CONTROL_WARD': stats[creator]['control_wards_placed']+=1
                elif ev['type'] == 'WARD_KILL':
                    if ev.get('killerId', 0) > 0: stats[ev['killerId']]['wards_killed']+=1
        return stats

    def _extract_midgame_stats(self, timeline_data, frames_10_stats):
        stats = {i: {'k':0, 'd':0, 'a':0, 'cs':0, 'gold':0, 'xp':0} for i in range(1, 11)}
        if not timeline_data: return stats
        frames = timeline_data['info']['frames']
        end_idx = 20 if len(frames) > 20 else len(frames)-1
        for pid_str, p in frames[end_idx]['participantFrames'].items():
            pid = int(pid_str)
            st_10 = frames_10_stats.get(pid, {})
            stats[pid]['cs'] = max(0, (p['minionsKilled'] + p['jungleMinionsKilled']) - st_10.get('cs', 0))
            stats[pid]['gold'] = max(0, p['totalGold'] - st_10.get('gold_total', 0))
            stats[pid]['xp'] = max(0, p['xp'] - st_10.get('xp', 0))
        start_ms, end_ms = 600000, 1200000
        for frame in frames:
            for ev in frame['events']:
                if ev['timestamp'] < start_ms: continue
                if ev['timestamp'] > end_ms: break
                if ev['type'] == 'CHAMPION_KILL':
                    k, v = ev.get('killerId', 0), ev.get('victimId', 0)
                    if k>0: stats[k]['k']+=1
                    if v>0: stats[v]['d']+=1
                    for a in ev.get('assistingParticipantIds', []):
                        if a>0: stats[a]['a']+=1
        return stats

    def _extract_lategame_stats(self, timeline_data):
        stats = {i: {'k':0, 'd':0, 'a':0, 'baron':0} for i in range(1, 11)}
        if not timeline_data: return stats
        start_ms = 1200000
        for frame in timeline_data['info']['frames']:
            for ev in frame['events']:
                if ev['timestamp'] < start_ms: continue
                if ev['type'] == 'CHAMPION_KILL':
                    k, v = ev.get('killerId', 0), ev.get('victimId', 0)
                    if k>0: stats[k]['k']+=1
                    if v>0: stats[v]['d']+=1
                    for a in ev.get('assistingParticipantIds', []):
                        if a>0: stats[a]['a']+=1
                elif ev['type'] == 'ELITE_MONSTER_KILL' and ev.get('monsterType') == 'BARON_NASHOR':
                    if ev.get('killerId', 0) > 0: stats[ev['killerId']]['baron']+=1
        return stats
    
    def _count_dragon_types(self, timeline_data, id_to_team):
        dragons = {100: {'AIR_DRAGON': 0, 'FIRE_DRAGON': 0, 'EARTH_DRAGON': 0, 'WATER_DRAGON': 0, 'HEX_DRAGON': 0, 'CHEM_DRAGON': 0, 'ELDER_DRAGON': 0},
                   200: {'AIR_DRAGON': 0, 'FIRE_DRAGON': 0, 'EARTH_DRAGON': 0, 'WATER_DRAGON': 0, 'HEX_DRAGON': 0, 'CHEM_DRAGON': 0, 'ELDER_DRAGON': 0}}
        if not timeline_data: return dragons
        for frame in timeline_data['info']['frames']:
            for ev in frame['events']:
                if ev['type'] == 'ELITE_MONSTER_KILL' and ev.get('monsterType') == 'DRAGON':
                    tid = id_to_team.get(ev.get('killerId', 0))
                    subtype = ev.get('monsterSubType')
                    if tid in dragons and subtype in dragons[tid]: dragons[tid][subtype] += 1
        return dragons

    def process_match_full(self, match_id):
        match_data = self._request(f"{self.routing_url}/lol/match/v5/matches/{match_id}")
        if not match_data or 'info' not in match_data: return None, None, None
        info = match_data['info']
        if info.get('queueId', 0) not in [420, 440]: return None, None, None

        timeline_data = self._request(f"{self.routing_url}/lol/match/v5/matches/{match_id}/timeline")
        
        early_10 = self._extract_timeline_snapshot(timeline_data, 10)
        early_15 = self._extract_timeline_snapshot(timeline_data, 15)
        mid = self._extract_midgame_stats(timeline_data, early_10)
        late = self._extract_lategame_stats(timeline_data)

        parts, teams = info['participants'], info['teams']
        id_to_team = {p['participantId']: p['teamId'] for p in parts}
        id_to_puuid = {p['participantId']: p['puuid'] for p in parts}
        id_to_name = {p['participantId']: (p.get('riotIdGameName') or p.get('summonerName')) for p in parts}
        
        team_kills_10 = {100: 0, 200: 0}
        for p in parts:
            if p['participantId'] in early_10: team_kills_10[p['teamId']] += early_10[p['participantId']]['k']

        dragons_detailed = self._count_dragon_types(timeline_data, id_to_team)
        perf_rows, kill_rows, team_rows = [], [], []
        df_parts = pd.DataFrame(parts)

        for p in parts:
            pid, tid = p['participantId'], p['teamId']
            e, e15, m, l = early_10.get(pid,{}), early_15.get(pid,{}), mid.get(pid,{}), late.get(pid,{'k':0,'d':0,'a':0,'baron':0})
            kp_10_val = (e.get('k',0) + e.get('a',0)) / max(team_kills_10.get(tid, 1), 1)
            
            mastery = self.get_champion_mastery(p['puuid'], p['championId'])
            perks, chal = p.get('perks', {}), p.get('challenges', {})

            row = {
                'match_id': match_id, 'match_team_key': f"{match_id}-{tid}",
                'puuid': p['puuid'], 'summoner_name': id_to_name[pid],
                'game_version': info['gameVersion'], 'game_duration_sec': info['gameDuration'],
                'game_start_timestamp': info['gameCreation'],
                'champion_name': p['championName'], 'team_id': tid, 'team_position': p.get('teamPosition', 'UNKNOWN'), 'win': p['win'],

                'total_gold_earned': p['goldEarned'], 
                'gold_spent': p.get('goldSpent', 0),
                'total_cs': p['totalMinionsKilled'] + p['neutralMinionsKilled'],
                'neutral_minions_killed': p['neutralMinionsKilled'],
                
                'total_cs': p['totalMinionsKilled'] + p['neutralMinionsKilled'],
                'neutral_minions_killed': p['neutralMinionsKilled'],
                
                'primary_rune_id': perks['styles'][0]['selections'][0]['perk'] if 'styles' in perks else None,
                'secondary_style_id': perks['styles'][1]['style'] if 'styles' in perks else None,
                'summoner_spell1': p['summoner1Id'], 'summoner_spell2': p['summoner2Id'], 'champion_mastery': mastery,

                'kills': p['kills'], 'deaths': p['deaths'], 'assists': p['assists'],
                'total_damage_dealt': p['totalDamageDealtToChampions'], 'physical_damage_dealt': p['physicalDamageDealtToChampions'],
                'magic_damage_dealt': p['magicDamageDealtToChampions'], 'true_damage_dealt': p['trueDamageDealtToChampions'],
                'total_damage_taken': p.get('totalDamageTaken',0), 'damage_self_mitigated': p.get('damageSelfMitigated',0),
                'total_gold_earned': p['goldEarned'], 'total_cs': p['totalMinionsKilled'] + p['neutralMinionsKilled'],
                'gold_per_min': round(p['goldEarned'] / (info['gameDuration']/60), 2),
                'cs_per_min': round((p['totalMinionsKilled'] + p['neutralMinionsKilled']) / (info['gameDuration']/60), 2),
                
                'vision_score': p['visionScore'], 'vision_wards_bought': p.get('visionWardsBoughtInGame',0),
                'time_cc_others': p.get('timeCCingOthers',0), 'total_heals_on_teammates': p.get('totalHealsOnTeammates',0),
                'total_shields_on_teammates': p.get('totalDamageShieldedOnTeammates',0),
                'total_time_spent_dead': p.get('totalTimeSpentDead',0), 'damage_to_objectives': p.get('damageDealtToObjectives',0),
                
                'solo_kills': chal.get('soloKills',0), 'multikills': chal.get('multikills',0), 
                'pentakills': p.get('pentaKills',0), 'objectives_stolen': chal.get('objectivesStolen',0), 
                'skillshots_dodged': chal.get('skillshotsDodged',0), 'first_blood_kill': p.get('firstBloodKill',False), 
                'spell_vamp': p.get('spellVamp',0)+p.get('physicalVamp',0), 'kda': chal.get('kda',0), 'kill_participation': chal.get('killParticipation',0),
                'item0':p.get('item0',0), 'item1':p.get('item1',0), 'item2':p.get('item2',0), 'item3':p.get('item3',0), 'item4':p.get('item4',0), 'item5':p.get('item5',0), 'item6':p.get('item6',0),
                
                'cs_at_10': e.get('cs',0), 'jungle_cs_at_10': e.get('jungle_cs', 0), 'lane_cs_at_10': e.get('lane_cs', 0),
                'gold_at_10': e.get('gold_total',0), 'xp_at_10': e.get('xp',0), 'level_at_10': e.get('level',1),
                'kills_at_10': e.get('k',0), 'deaths_at_10': e.get('d',0), 'assists_at_10': e.get('a',0),
                'solo_kills_at_10': e.get('solo_k',0), 'turret_plates_taken': e.get('plates',0), 'kp_at_10': round(kp_10_val, 2),
                'gold_spent_at_10': e.get('gold_total',0) - e.get('gold_current',0),
                'wards_placed_at_10': e.get('wards_placed',0), 'control_wards_placed_at_10': e.get('control_wards_placed',0),
                'wards_killed_at_10': e.get('wards_killed',0),

                'cs_at_15': e15.get('cs',0), 'gold_at_15': e15.get('gold_total',0), 'xp_at_15': e15.get('xp',0),
                'gold_gain_10_20': m.get('gold',0), 'xp_gain_10_20': m.get('xp',0), 'cs_gain_10_20': m.get('cs',0),
                'kills_10_20': m.get('k',0), 'deaths_10_20': m.get('d',0), 'assists_10_20': m.get('a',0),
                'kills_20_plus': l['k'], 'deaths_20_plus': l['d'], 'assists_20_plus': l['a'], 'baron_kills_20_plus': l['baron']
            }
            # Diff Calc
            if p.get('teamPosition') != 'UNKNOWN':
                opp = df_parts[(df_parts['teamPosition']==p['teamPosition']) & (df_parts['teamId']!=tid)]
                if not opp.empty:
                    opid = opp.iloc[0]['participantId']
                    oe, oe15 = early_10.get(opid, {}), early_15.get(opid, {})
                    row.update({'cs_diff_at_10': row['cs_at_10']-oe.get('cs',0), 'gold_diff_at_10': row['gold_at_10']-oe.get('gold_total',0), 'xp_diff_at_10': row['xp_at_10']-oe.get('xp',0),
                                'cs_diff_at_15': row['cs_at_15']-oe15.get('cs',0), 'gold_diff_at_15': row['gold_at_15']-oe15.get('gold_total',0), 'xp_diff_at_15': row['xp_at_15']-oe15.get('xp',0)})
                else: row.update({'cs_diff_at_10':0, 'gold_diff_at_10':0, 'xp_diff_at_10':0, 'cs_diff_at_15':0, 'gold_diff_at_15':0, 'xp_diff_at_15':0})
            else: row.update({'cs_diff_at_10':0, 'gold_diff_at_10':0, 'xp_diff_at_10':0, 'cs_diff_at_15':0, 'gold_diff_at_15':0, 'xp_diff_at_15':0})
            perf_rows.append(row)

        if timeline_data:
            for frame in timeline_data['info']['frames']:
                for ev in frame['events']:
                    if ev['type'] == 'CHAMPION_KILL':
                        vid, kid = ev.get('victimId',0), ev.get('killerId',0)
                        pos = ev.get('position',{})
                        kill_rows.append({
                            'death_id': f"{match_id}_{ev['timestamp']}_{vid}", 'match_id': match_id, 'event_time_min': round(ev['timestamp']/60000, 2),
                            'victim_id': vid, 'victim_puuid': id_to_puuid.get(vid,''), 'victim_name': id_to_name.get(vid,''), 'victim_team_id': id_to_team.get(vid,0),
                            'killer_id': kid, 'killer_puuid': id_to_puuid.get(kid,''), 'killer_name': id_to_name.get(kid,''),
                            'pos_x': pos.get('x',0), 'pos_y': pos.get('y',0), 'is_in_base': (pos.get('x',0)<2000 and pos.get('y',0)<2000) or (pos.get('x',0)>12800 and pos.get('y',0)>12800)
                        })

        for t in teams:
            d_stats = dragons_detailed.get(t['teamId'], {})
            o = t.get('objectives',{})
            team_rows.append({
                'match_id': match_id, 'match_team_key': f"{match_id}-{t['teamId']}", 'team_id': t['teamId'], 'win': t['win'],
                'baron_kills': o.get('baron',{}).get('kills',0), 'dragon_kills': o.get('dragon',{}).get('kills',0), 'tower_kills': o.get('tower',{}).get('kills',0),
                'inhibitor_kills': o.get('inhibitor',{}).get('kills',0), 'horde_kills': o.get('horde',{}).get('kills',0),
                'cloud_kills': d_stats.get('AIR_DRAGON',0), 'infernal_kills': d_stats.get('FIRE_DRAGON',0), 'mountain_kills': d_stats.get('EARTH_DRAGON',0),
                'ocean_kills': d_stats.get('WATER_DRAGON',0), 'hextech_kills': d_stats.get('HEX_DRAGON',0), 'chemtech_kills': d_stats.get('CHEM_DRAGON',0), 'elder_kills': d_stats.get('ELDER_DRAGON',0)
            })
        return perf_rows, kill_rows, team_rows

    def upsert(self, table, data, keys):
        if not data: return
        try:
            with self.engine.connect() as conn:
                stmt = insert(table).values(data)
                stmt = stmt.on_conflict_do_nothing(index_elements=keys)
                conn.execute(stmt)
                conn.commit()
        except Exception as e:
            logger.error(f"Erro DB {table.name}: {e}")