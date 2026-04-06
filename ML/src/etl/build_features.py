#!/usr/bin/env python3
"""
FASE 2 - Feature Engineering Básico y Rolling Features
Calcula features temporales (últimos N partidos), rest days, injury counts, implied probs
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm
from src.config import db_config


def build_features():
    """
    Construye features de ingeniería para ml_ready_games
    """
    print("=" * 60)
    print("[*] FASE 2: Feature Engineering Básico y Rolling Features")
    print("=" * 60)
    print()
    
    # Configurar conexión
    database_url = db_config.get_database_url()
    ml_schema = db_config.get_schema("ml")
    espn_schema = db_config.get_schema("espn")
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {ml_schema}, {espn_schema}, public"))
            conn.commit()
        
        print("[>] Paso 1: Cargando datos desde Neon...")
        print("-" * 60)
        
        # 1) Cargar games y otras tablas necesarias
        print("   Cargando espn.games...")
        games = pd.read_sql(
            f"SELECT * FROM {espn_schema}.games ORDER BY fecha",
            engine
        )
        print(f"   [OK] {len(games)} partidos cargados")
        
        print("   Cargando espn.game_id_mapping...")
        try:
            mapping = pd.read_sql(
                f"SELECT espn_id, nba_id FROM {espn_schema}.game_id_mapping",
                engine
            )
            # Normalizar tipos para join
            games['game_id_str'] = games['game_id'].astype(str)
            games = games.merge(mapping, left_on='game_id_str', right_on='espn_id', how='left')
            print(f"   [OK] Mapeo de IDs cargado y aplicado ({games['nba_id'].count()} coincidencias)")
        except Exception as e:
            print(f"   [!]  No se pudo cargar game_id_mapping: {e}")
            games['nba_id'] = None
        
        print("   Cargando espn.nba_player_boxscores...")
        try:
            player_box = pd.read_sql(
                f"SELECT game_id, team_tricode, pts, fga, fgm, fta, ftm, three_pa, three_pm, oreb, dreb, ast, stl, blk, to_stat as tov FROM {espn_schema}.nba_player_boxscores",
                engine
            )
            # COVERTIR game_id A BIGINT PARA MATCHING
            player_box['game_id'] = pd.to_numeric(player_box['game_id'], errors='coerce').astype('Int64')
            print(f"   [OK] {len(player_box)} registros loaded")
            
            # Debug: Check a few game IDs
            print(f"   [DEBUG] Sample Boxscore Game IDs: {player_box['game_id'].dropna().head(3).tolist()}")
            
            # Agregar boxscores a nivel de equipo
            print("   Agregando estadísticas a nivel de equipo...")
            player_box = player_box.dropna(subset=['game_id'])
            
            team_game_stats = player_box.groupby(['game_id', 'team_tricode']).agg({
                'pts': 'sum',
                'fga': 'sum',
                'fgm': 'sum',
                'fta': 'sum',
                'ftm': 'sum',
                'three_pa': 'sum',
                'three_pm': 'sum',
                'oreb': 'sum',
                'dreb': 'sum',
                'ast': 'sum',
                'stl': 'sum',
                'blk': 'sum',
                'tov': 'sum'
            }).reset_index()
            
            # Calcular posesiones por equipo (fórmula simplificada)
            # Poss = FGA + 0.44 * FTA - ORB + TOV
            team_game_stats['poss'] = (
                team_game_stats['fga'] + 
                0.44 * team_game_stats['fta'] - 
                team_game_stats['oreb'] + 
                team_game_stats['tov']
            )
            print(f"   [OK] Estadísticas de equipo calculadas para {len(team_game_stats)} registros")
        except Exception as e:
            print(f"   [!]  No se pudo cargar o procesar nba_player_boxscores: {e}")
            print(e)
            team_game_stats = pd.DataFrame()
        
        print("   Cargando espn.injuries...")
        try:
            injuries = pd.read_sql(
                f"SELECT * FROM {espn_schema}.injuries",
                engine
            )
            print(f"   [OK] {len(injuries)} registros de lesiones cargados")
        except Exception as e:
            print(f"   [!]  No se pudo cargar injuries: {e}")
            injuries = pd.DataFrame()
        
        print("   Cargando espn.odds...")
        try:
            # En Neon, ml.ml_ready_games ya tiene las odds si usamos map_odds_to_games
            # pero aquí build_features calcula features adicionales
            odds = pd.read_sql(
                f"SELECT * FROM {espn_schema}.odds",
                engine
            )
            print(f"   [OK] {len(odds)} registros de cuotas cargados")
        except Exception as e:
            print(f"   [!]  No se pudo cargar odds: {e}")
            odds = pd.DataFrame()
        
        print()
        
        # 2) Normalizar nombres de equipos
        print("[>] Paso 2: Normalizando nombres de equipos...")
        print("-" * 60)
        
        # Mapeo de tricode a nombre de equipo si es necesario
        # (Aunque nba_player_boxscores usa tricode, games usa nombres completos)
        # Vamos a usar el mapping que ya existe en la base de datos si es posible
        print("   [OK] Usando nombres completos de equipos (no abreviaciones)")
        print()
        
        # 3) Helper: construir rolling aggregates por equipo
        print("[>] Paso 3: Calculando rolling features...")
        print("-" * 60)

        def compute_elo(df_games, K=20, home_advantage=100, initial=1500):
            """Calcula Elo rating para cada equipo ANTES de cada juego."""
            elo = {}
            game_elos = {}
            for _, row in df_games.sort_values('fecha').iterrows():
                home, away = row['home_team'], row['away_team']
                gid = row['game_id']
                h_elo = elo.get(home, initial)
                a_elo = elo.get(away, initial)
                game_elos[(gid, home)] = h_elo
                game_elos[(gid, away)] = a_elo
                h_pts = row.get('home_pts') or row.get('home_score') or 0
                a_pts = row.get('away_pts') or row.get('away_score') or 0
                if h_pts == 0 and a_pts == 0:
                    continue
                exp_h = 1 / (1 + 10 ** ((a_elo - h_elo - home_advantage) / 400))
                actual_h = 1.0 if h_pts > a_pts else 0.0
                elo[home] = h_elo + K * (actual_h - exp_h)
                elo[away] = a_elo + K * ((1 - actual_h) - (1 - exp_h))
            return game_elos

        def compute_h2h(df_games, n_recent=5):
            """Para cada juego, calcula wins del home en últimos n_recent enfrentamientos."""
            h2h = {}
            matchup_history = {}
            for _, row in df_games.sort_values('fecha').iterrows():
                home, away, gid = row['home_team'], row['away_team'], row['game_id']
                key = tuple(sorted([home, away]))
                history = matchup_history.get(key, [])
                recent = history[-n_recent:] if history else []
                home_wins = sum(1 for _, w in recent if w == home)
                h2h[gid] = home_wins / max(len(recent), 1)
                h_pts = row.get('home_pts') or row.get('home_score') or 0
                a_pts = row.get('away_pts') or row.get('away_score') or 0
                if h_pts > 0 or a_pts > 0:
                    winner = home if h_pts > a_pts else away
                    matchup_history.setdefault(key, []).append((row['fecha'], winner))
            return h2h

        def rolling_stats(df_games, df_team_stats):
            """
            Construye estadísticas rolling por equipo
            """
            rows = []
            
            # Mapeo de ID (as numeric) a estadísticas de equipo para acceso rápido
            stats_map = {}
            if not df_team_stats.empty:
                for _, row in df_team_stats.iterrows():
                    try:
                        gid_num = int(row['game_id'])
                        stats_map[(gid_num, row['team_tricode'])] = row.to_dict()
                    except:
                        continue

            # Mapeo de nombres de equipos a tricodes (aproximado)
            team_name_to_tricode = {
                'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
                'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
                'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
                'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
                'LA Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
                'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
                'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
                'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
                'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
                'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
            }
            
            for _, r in tqdm(df_games.iterrows(), total=len(df_games), desc="   Procesando partidos"):
                game_id = r['game_id']
                home_team = r['home_team']
                away_team = r['away_team']
                fecha = pd.to_datetime(r['fecha'])
                
                # FALLBACK PARA SCORE
                home_pts = r['home_pts'] if pd.notna(r.get('home_pts')) else (r['home_score'] if pd.notna(r.get('home_score')) else 0)
                away_pts = r['away_pts'] if pd.notna(r.get('away_pts')) else (r['away_score'] if pd.notna(r.get('away_score')) else 0)
                
                # FALLBACK PARA NET RATING
                net_rating_diff = r.get('net_rating_diff', 0)
                if pd.isna(net_rating_diff):
                    net_rating_diff = home_pts - away_pts # Simple diff if net_rating missing
                if pd.isna(net_rating_diff):
                    net_rating_diff = 0
                
                # Buscar stats avanzadas
                home_tricode = team_name_to_tricode.get(home_team)
                away_tricode = team_name_to_tricode.get(away_team)
                
                # NORMALIZAR lookup_id A NUMERIC
                lookup_id = None
                if pd.notna(r.get('nba_id')):
                    try:
                        lookup_id = int(r['nba_id'])
                    except:
                        lookup_id = int(game_id)
                else:
                    lookup_id = int(game_id)
                
                home_stats = stats_map.get((lookup_id, home_tricode), {})
                away_stats = stats_map.get((lookup_id, away_tricode), {})
                home_has_box = bool(home_stats)
                away_has_box = bool(away_stats)

                home_poss = home_stats.get('poss', None)
                away_poss = away_stats.get('poss', None)

                # Base Stats extraction [?] NaN when no boxscore data
                def get_stat(stats, key, has_box):
                    if not has_box:
                        return np.nan
                    return stats.get(key, 0)
                
                # Rebounds
                h_oreb = get_stat(home_stats, 'oreb', home_has_box)
                h_dreb = get_stat(home_stats, 'dreb', home_has_box)
                h_reb = h_oreb + h_dreb

                a_oreb = get_stat(away_stats, 'oreb', away_has_box)
                a_dreb = get_stat(away_stats, 'dreb', away_has_box)
                a_reb = a_oreb + a_dreb

                # Assists, Steals, Blocks, TOV
                h_ast = get_stat(home_stats, 'ast', home_has_box)
                h_stl = get_stat(home_stats, 'stl', home_has_box)
                h_blk = get_stat(home_stats, 'blk', home_has_box)
                h_tov = get_stat(home_stats, 'tov', home_has_box)

                a_ast = get_stat(away_stats, 'ast', away_has_box)
                a_stl = get_stat(away_stats, 'stl', away_has_box)
                a_blk = get_stat(away_stats, 'blk', away_has_box)
                a_tov = get_stat(away_stats, 'tov', away_has_box)

                # Percentages [?] NaN when no boxscore
                h_fgm = get_stat(home_stats, 'fgm', home_has_box)
                h_fga = get_stat(home_stats, 'fga', home_has_box)
                h_fg_pct = (h_fgm / h_fga) if (home_has_box and h_fga > 0) else np.nan if not home_has_box else 0.0

                a_fgm = get_stat(away_stats, 'fgm', away_has_box)
                a_fga = get_stat(away_stats, 'fga', away_has_box)
                a_fg_pct = (a_fgm / a_fga) if (away_has_box and a_fga > 0) else np.nan if not away_has_box else 0.0

                h_fg3m = get_stat(home_stats, 'three_pm', home_has_box)
                h_fg3a = get_stat(home_stats, 'three_pa', home_has_box)
                h_fg3_pct = (h_fg3m / h_fg3a) if (home_has_box and h_fg3a > 0) else np.nan if not home_has_box else 0.0

                a_fg3m = get_stat(away_stats, 'three_pm', away_has_box)
                a_fg3a = get_stat(away_stats, 'three_pa', away_has_box)
                a_fg3_pct = (a_fg3m / a_fg3a) if (away_has_box and a_fg3a > 0) else np.nan if not away_has_box else 0.0

                h_ftm = get_stat(home_stats, 'ftm', home_has_box)
                h_fta = get_stat(home_stats, 'fta', home_has_box)
                h_ft_pct = (h_ftm / h_fta) if (home_has_box and h_fta > 0) else np.nan if not home_has_box else 0.0

                a_ftm = get_stat(away_stats, 'ftm', away_has_box)
                a_fta = get_stat(away_stats, 'fta', away_has_box)
                a_ft_pct = (a_ftm / a_fta) if (away_has_box and a_fta > 0) else np.nan if not away_has_box else 0.0
                
                # Si tenemos posesiones, calculamos ratings individuales de este partido
                home_off_rtg = (home_pts / home_poss * 100) if home_poss and home_poss > 0 else None
                away_off_rtg = (away_pts / away_poss * 100) if away_poss and away_poss > 0 else None
                
                # Pace (partido individual)
                game_pace = (home_poss + away_poss) / 2 if home_poss and away_poss else None
                
                # EFG%: (FGM + 0.5 * 3PM) / FGA
                h_efg_pct = ((h_fgm + 0.5 * h_fg3m) / h_fga) if (home_has_box and not np.isnan(h_fga) and h_fga > 0) else np.nan
                a_efg_pct = ((a_fgm + 0.5 * a_fg3m) / a_fga) if (away_has_box and not np.isnan(a_fga) and a_fga > 0) else np.nan

                # Turnover Rate: TOV / (FGA + 0.44*FTA + TOV)
                h_tov_denom = h_fga + 0.44 * h_fta + h_tov if home_has_box else np.nan
                h_tov_rate = (h_tov / h_tov_denom) if (home_has_box and not np.isnan(h_tov_denom) and h_tov_denom > 0) else np.nan
                a_tov_denom = a_fga + 0.44 * a_fta + a_tov if away_has_box else np.nan
                a_tov_rate = (a_tov / a_tov_denom) if (away_has_box and not np.isnan(a_tov_denom) and a_tov_denom > 0) else np.nan

                # OReb%: OREB / (OREB + OPP_DREB)
                h_oreb_pct = (h_oreb / (h_oreb + a_dreb)) if (home_has_box and away_has_box and not np.isnan(h_oreb) and (h_oreb + a_dreb) > 0) else np.nan
                a_oreb_pct = (a_oreb / (a_oreb + h_dreb)) if (away_has_box and home_has_box and not np.isnan(a_oreb) and (a_oreb + h_dreb) > 0) else np.nan

                # DReb%: DREB / (DREB + OPP_OREB)
                h_dreb_pct = (h_dreb / (h_dreb + a_oreb)) if (home_has_box and away_has_box and not np.isnan(h_dreb) and (h_dreb + a_oreb) > 0) else np.nan
                a_dreb_pct = (a_dreb / (a_dreb + h_oreb)) if (away_has_box and home_has_box and not np.isnan(a_dreb) and (a_dreb + h_oreb) > 0) else np.nan

                rows.append({
                    'game_id': game_id,
                    'fecha': fecha,
                    'team': home_team,
                    'opponent': away_team,
                    'is_home': True,
                    'pts': home_pts,
                    'opp_pts': away_pts,
                    'net_rating': net_rating_diff,
                    'poss': home_poss,
                    'off_rtg': home_off_rtg,
                    'pace': game_pace,
                    'fg_pct': h_fg_pct, 'fg3_pct': h_fg3_pct, 'ft_pct': h_ft_pct,
                    'reb': h_reb, 'ast': h_ast, 'stl': h_stl, 'blk': h_blk, 'tov': h_tov,
                    'efg_pct': h_efg_pct, 'tov_rate': h_tov_rate,
                    'oreb_pct': h_oreb_pct, 'dreb_pct': h_dreb_pct,
                })

                rows.append({
                    'game_id': game_id,
                    'fecha': fecha,
                    'team': away_team,
                    'opponent': home_team,
                    'is_home': False,
                    'pts': away_pts,
                    'opp_pts': home_pts,
                    'net_rating': -net_rating_diff,
                    'poss': away_poss,
                    'off_rtg': away_off_rtg,
                    'pace': game_pace,
                    'fg_pct': a_fg_pct, 'fg3_pct': a_fg3_pct, 'ft_pct': a_ft_pct,
                    'reb': a_reb, 'ast': a_ast, 'stl': a_stl, 'blk': a_blk, 'tov': a_tov,
                    'efg_pct': a_efg_pct, 'tov_rate': a_tov_rate,
                    'oreb_pct': a_oreb_pct, 'dreb_pct': a_dreb_pct,
                })
            
            tt = pd.DataFrame(rows).sort_values(['team', 'fecha', 'game_id'])
            
            # Rolling averages
            # PPG
            tt['pts_last5'] = tt.groupby('team')['pts'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )
            # Net Rating
            tt['net_last10'] = tt.groupby('team')['net_rating'].transform(
                lambda x: x.shift(1).rolling(window=10, min_periods=1).mean()
            )
            # Pace
            tt['pace_last5'] = tt.groupby('team')['pace'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )
            # Offensive Rating
            tt['off_rtg_last5'] = tt.groupby('team')['off_rtg'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )
            # Defensive Rating (Points allowed / Possessions)
            # Simplified: Use opp_pts rolling / poss rolling
            tt['opp_pts_last5'] = tt.groupby('team')['opp_pts'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).sum()
            )
            tt['poss_last5'] = tt.groupby('team')['poss'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).sum()
            )
            tt['def_rtg_last5'] = (tt['opp_pts_last5'] / tt['poss_last5'] * 100).where(tt['poss_last5'] > 0, None)

            # Rolling reb / ast / tov [?] shift(1) garantiza que solo se usan partidos ANTERIORES
            # (home_reb/ast/tov sin rolling son del partido actual -> leakage)
            tt['reb_last5'] = tt.groupby('team')['reb'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )
            tt['ast_last5'] = tt.groupby('team')['ast'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )
            tt['tov_last5'] = tt.groupby('team')['tov'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )

            # Win rate rolling (tasa de victorias en últimos 10 partidos)
            tt['win'] = (tt['pts'] > tt['opp_pts']).astype(int)
            tt['win_rate_last10'] = tt.groupby('team')['win'].transform(
                lambda x: x.shift(1).rolling(window=10, min_periods=1).mean()
            )

            # === NUEVAS FEATURES v2 ===

            # EFG% rolling (últimos 5 partidos)
            tt['efg_pct_last5'] = tt.groupby('team')['efg_pct'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )

            # Turnover Rate rolling (últimos 5 partidos)
            tt['tov_rate_last5'] = tt.groupby('team')['tov_rate'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )

            # OReb% rolling (últimos 5 partidos)
            tt['oreb_pct_last5'] = tt.groupby('team')['oreb_pct'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )

            # DReb% rolling (últimos 5 partidos)
            tt['dreb_pct_last5'] = tt.groupby('team')['dreb_pct'].transform(
                lambda x: x.shift(1).rolling(window=5, min_periods=1).mean()
            )

            # Streak: rachas consecutivas de victorias (+) o derrotas (-)
            def compute_streak(wins):
                streak = []
                current = 0
                for w in wins:
                    if pd.isna(w):
                        streak.append(0)
                        continue
                    current = max(0, current) + 1 if w == 1 else min(0, current) - 1
                    streak.append(current)
                return pd.Series(streak, index=wins.index)

            tt['streak'] = tt.groupby('team')['win'].transform(
                lambda x: compute_streak(x).shift(1).fillna(0)
            )

            # Home/Away splits: win rate solo en partidos como local o visitante
            tt['home_game_win'] = tt['win'].where(tt['is_home'], np.nan)
            tt['away_game_win'] = tt['win'].where(~tt['is_home'], np.nan)
            tt['home_win_rate_split'] = tt.groupby('team')['home_game_win'].transform(
                lambda x: x.shift(1).rolling(window=10, min_periods=3).mean()
            )
            tt['away_win_rate_split'] = tt.groupby('team')['away_game_win'].transform(
                lambda x: x.shift(1).rolling(window=10, min_periods=3).mean()
            )

            return tt
        
        tt = rolling_stats(games, team_game_stats)
        print(f"   [OK] Rolling features calculadas para {len(tt)} registros")

        # Elo ratings (cumulative, leakage-free by design)
        print("   Calculando Elo ratings...")
        elo_map = compute_elo(games)
        tt['elo'] = tt.apply(lambda r: elo_map.get((r['game_id'], r['team']), 1500), axis=1)
        print(f"   [OK] Elo calculado para {tt['elo'].notna().sum()} registros")

        # H2H (home team advantage in last 5 matchups)
        print("   Calculando H2H...")
        h2h_map = compute_h2h(games)
        # H2H solo se asigna al row del home team; away se calcula como inverso
        tt['h2h_home_wins_last5'] = tt.apply(
            lambda r: h2h_map.get(r['game_id'], 0.5) if r['is_home'] else (1.0 - h2h_map.get(r['game_id'], 0.5)),
            axis=1
        )
        print(f"   [OK] H2H calculado")
        print()
        
        # 4) Merge rolling features back into ml_ready_games
        print("[>] Paso 4: Aplicando rolling features a ml_ready_games...")
        print("-" * 60)
        
        # Leer ml_ready_games
        print("   Cargando ml_ready_games...")
        ml = pd.read_sql(
            f"SELECT * FROM {ml_schema}.ml_ready_games",
            engine
        )
        print(f"   [OK] {len(ml)} registros cargados")
        
        # Merge tt with ml
        home_rename = {
            'pts_last5': 'home_ppg_last5',
            'net_last10': 'home_net_rating_last10',
            'pace_last5': 'home_pace_rolling',
            'off_rtg_last5': 'home_off_rating_rolling',
            'def_rtg_last5': 'home_def_rating_rolling',
            'fg_pct': 'home_fg_pct', 'fg3_pct': 'home_3p_pct', 'ft_pct': 'home_ft_pct',
            'reb': 'home_reb', 'ast': 'home_ast', 'stl': 'home_stl', 'blk': 'home_blk', 'tov': 'home_to',
            'reb_last5': 'home_reb_rolling',
            'ast_last5': 'home_ast_rolling',
            'tov_last5': 'home_tov_rolling',
            'win_rate_last10': 'home_win_rate_last10',
            # Nuevas features v2
            'efg_pct_last5': 'home_efg_pct_rolling',
            'tov_rate_last5': 'home_tov_rate_rolling',
            'oreb_pct_last5': 'home_oreb_pct_rolling',
            'dreb_pct_last5': 'home_dreb_pct_rolling',
            'elo': 'home_elo',
            'streak': 'home_streak',
            'home_win_rate_split': 'home_home_win_rate',
            'h2h_home_wins_last5': 'h2h_home_advantage',
        }
        home_cols = ['game_id'] + list(home_rename.values())
        tt_home = tt[tt['is_home'] == True].rename(columns=home_rename)[home_cols]

        away_rename = {
            'pts_last5': 'away_ppg_last5',
            'net_last10': 'away_net_rating_last10',
            'pace_last5': 'away_pace_rolling',
            'off_rtg_last5': 'away_off_rating_rolling',
            'def_rtg_last5': 'away_def_rating_rolling',
            'fg_pct': 'away_fg_pct', 'fg3_pct': 'away_3p_pct', 'ft_pct': 'away_ft_pct',
            'reb': 'away_reb', 'ast': 'away_ast', 'stl': 'away_stl', 'blk': 'away_blk', 'tov': 'away_to',
            'reb_last5': 'away_reb_rolling',
            'ast_last5': 'away_ast_rolling',
            'tov_last5': 'away_tov_rolling',
            'win_rate_last10': 'away_win_rate_last10',
            # Nuevas features v2
            'efg_pct_last5': 'away_efg_pct_rolling',
            'tov_rate_last5': 'away_tov_rate_rolling',
            'oreb_pct_last5': 'away_oreb_pct_rolling',
            'dreb_pct_last5': 'away_dreb_pct_rolling',
            'elo': 'away_elo',
            'streak': 'away_streak',
            'away_win_rate_split': 'away_away_win_rate',
        }
        away_cols = ['game_id'] + [v for v in away_rename.values()]
        tt_away = tt[tt['is_home'] == False].rename(columns=away_rename)[away_cols]

        # Limpiar ml de columnas que vamos a sobreescribir para evitar duplicados en el merge
        cols_to_drop = list(set(
            list(home_rename.values()) + [v for v in away_rename.values()]
        ))
        ml = ml.drop(columns=[c for c in cols_to_drop if c in ml.columns])
        
        ml = ml.merge(tt_home, on='game_id', how='left')
        ml = ml.merge(tt_away, on='game_id', how='left')
        
        print("   [OK] Rolling features aplicadas")
        print()
        
        # 5) Rest days and B2B
        print("[>] Paso 5: Calculando días de descanso y B2B...")
        print("-" * 60)
        
        games_dates = games[['game_id', 'fecha', 'home_team', 'away_team']].copy()
        games_dates['fecha'] = pd.to_datetime(games_dates['fecha'])
        games_dates = games_dates.sort_values('fecha')
        
        last_dates = {}
        rest_home = []
        rest_away = []
        
        for _, row in tqdm(games_dates.iterrows(), total=len(games_dates), desc="   Calculando rest days"):
            gid = row['game_id']
            home = row['home_team']
            away = row['away_team']
            date = row['fecha']
            
            last_home = last_dates.get(home, None)
            last_away = last_dates.get(away, None)
            
            rest_home.append((date - last_home).days if last_home is not None else None)
            rest_away.append((date - last_away).days if last_away is not None else None)
            
            last_dates[home] = date
            last_dates[away] = date
        
        rest_df = pd.DataFrame({
            'game_id': games_dates['game_id'].values,
            'home_rest_days': rest_home,
            'away_rest_days': rest_away
        })
        
        # B2B logic
        rest_df['home_b2b'] = rest_df['home_rest_days'] == 1
        rest_df['away_b2b'] = rest_df['away_rest_days'] == 1
        
        # Merge
        ml = ml.drop(columns=['home_rest_days', 'away_rest_days', 'home_b2b', 'away_b2b'], errors='ignore')
        ml = ml.merge(rest_df, on='game_id', how='left')
        
        print(f"   [OK] Días de descanso y B2B calculados")
        print()
        
        # 6) Contar lesiones
        print("[>] Paso 6: Contando lesiones...")
        print("-" * 60)
        
        if not injuries.empty:
            team_col = next((c for c in ['team', 'team_name', 'team_id'] if c in injuries.columns), None)
            if team_col:
                # Mapping of nicknames (from injuries table) to full names (for matching ml_ready_games)
                nickname_to_fullname = {
                    '76ers': 'Philadelphia 76ers', 'Bucks': 'Milwaukee Bucks', 'Bulls': 'Chicago Bulls',
                    'Cavaliers': 'Cleveland Cavaliers', 'Celtics': 'Boston Celtics', 'Clippers': 'LA Clippers',
                    'Grizzlies': 'Memphis Grizzlies', 'Hawks': 'Atlanta Hawks', 'Heat': 'Miami Heat',
                    'Hornets': 'Charlotte Hornets', 'Jazz': 'Utah Jazz', 'Kings': 'Sacramento Kings',
                    'Knicks': 'New York Knicks', 'Lakers': 'Los Angeles Lakers', 'Magic': 'Orlando Magic',
                    'Mavericks': 'Dallas Mavericks', 'Nets': 'Brooklyn Nets', 'Nuggets': 'Denver Nuggets',
                    'Pacers': 'Indiana Pacers', 'Pelicans': 'New Orleans Pelicans', 'Pistons': 'Detroit Pistons',
                    'Raptors': 'Toronto Raptors', 'Rockets': 'Houston Rockets', 'Spurs': 'San Antonio Spurs',
                    'Suns': 'Phoenix Suns', 'Thunder': 'Oklahoma City Thunder', 'Timberwolves': 'Minnesota Timberwolves',
                    'Trail Blazers': 'Portland Trail Blazers', 'Warriors': 'Golden State Warriors', 'Wizards': 'Washington Wizards'
                }

                # Apply mapping
                injuries['mapped_team'] = injuries[team_col].map(nickname_to_fullname).fillna(injuries[team_col])
                
                inj_counts = injuries.groupby('mapped_team').size().to_dict()
                ml['home_injuries_count'] = ml['home_team'].map(lambda t: inj_counts.get(t, 0) if pd.notna(t) else 0)
                ml['away_injuries_count'] = ml['away_team'].map(lambda t: inj_counts.get(t, 0) if pd.notna(t) else 0)
            else:
                ml['home_injuries_count'] = 0
                ml['away_injuries_count'] = 0
        else:
            ml['home_injuries_count'] = 0
            ml['away_injuries_count'] = 0
        print()
        
        # 7) Calcular Diferenciales Finales
        print("[>] Paso 7: Calculando diferenciales finales...")
        print("-" * 60)
        
        ml['ppg_diff'] = ml['home_ppg_last5'] - ml['away_ppg_last5']
        ml['net_rating_diff_rolling'] = ml['home_net_rating_last10'] - ml['away_net_rating_last10']
        ml['pace_diff'] = ml['home_pace_rolling'] - ml['away_pace_rolling']
        ml['off_rating_diff'] = ml['home_off_rating_rolling'] - ml['away_off_rating_rolling']
        ml['def_rating_diff'] = ml['home_def_rating_rolling'] - ml['away_def_rating_rolling']
        
        # Base Stat Differentials (current-game stats [?] kept for reference/XGBoost)
        ml['reb_diff'] = ml['home_reb'] - ml['away_reb']
        ml['ast_diff'] = ml['home_ast'] - ml['away_ast']
        ml['tov_diff'] = ml['home_to'] - ml['away_to']

        # Rolling Stat Differentials [?] usa promedios de partidos ANTERIORES (sin leakage)
        ml['reb_rolling_diff'] = ml['home_reb_rolling'] - ml['away_reb_rolling']
        ml['ast_rolling_diff'] = ml['home_ast_rolling'] - ml['away_ast_rolling']
        ml['tov_rolling_diff'] = ml['home_tov_rolling'] - ml['away_tov_rolling']
        ml['win_rate_diff'] = ml['home_win_rate_last10'] - ml['away_win_rate_last10']

        ml['rest_days_diff'] = (ml['home_rest_days'].fillna(3) - ml['away_rest_days'].fillna(3)).astype(int)

        # Nuevos diferenciales v2
        ml['efg_pct_diff'] = ml['home_efg_pct_rolling'] - ml['away_efg_pct_rolling']
        ml['tov_rate_diff'] = ml['home_tov_rate_rolling'] - ml['away_tov_rate_rolling']
        ml['oreb_pct_diff'] = ml['home_oreb_pct_rolling'] - ml['away_oreb_pct_rolling']
        ml['dreb_pct_diff'] = ml['home_dreb_pct_rolling'] - ml['away_dreb_pct_rolling']
        ml['elo_diff'] = ml['home_elo'] - ml['away_elo']
        ml['streak_diff'] = ml['home_streak'] - ml['away_streak']
        ml['home_away_split_diff'] = ml['home_home_win_rate'] - ml['away_away_win_rate']
        ml['injuries_diff'] = ml['home_injuries_count'] - ml['away_injuries_count']
        
        print("   [OK] Diferenciales calculados")
        print()
        
        # 8) Odds Probs (si no están ya mapeadas)
        # Probabilidades implícitas si existen
        # (Omitimos el mapeo JSON manual si ya está en espn.game_odds)
        
        # Escribir a BD
        print("[>] Paso 8: Actualizando ml_ready_games en Neon...")
        print("-" * 60)
        
        # Seleccionar columnas finales
        final_cols = [
            'game_id', 'home_ppg_last5', 'away_ppg_last5',
            'home_net_rating_last10', 'away_net_rating_last10',
            'home_rest_days', 'away_rest_days',
            'home_injuries_count', 'away_injuries_count',
            'home_b2b', 'away_b2b',
            'home_pace_rolling', 'away_pace_rolling',
            'home_off_rating_rolling', 'away_off_rating_rolling',
            'home_def_rating_rolling', 'away_def_rating_rolling',
            'home_fg_pct', 'away_fg_pct', 'home_3p_pct', 'away_3p_pct',
            'home_ft_pct', 'away_ft_pct',
            # Current-game boxscore stats (no usar como features de clasificación)
            'home_reb', 'away_reb', 'home_ast', 'away_ast',
            'home_stl', 'away_stl', 'home_blk', 'away_blk', 'home_to', 'away_to',
            # Rolling stats por equipo (shift(1) -> sin leakage)
            'home_reb_rolling', 'away_reb_rolling',
            'home_ast_rolling', 'away_ast_rolling',
            'home_tov_rolling', 'away_tov_rolling',
            'home_win_rate_last10', 'away_win_rate_last10',
            # Nuevas features v2 (rolling, sin leakage)
            'home_efg_pct_rolling', 'away_efg_pct_rolling',
            'home_tov_rate_rolling', 'away_tov_rate_rolling',
            'home_oreb_pct_rolling', 'away_oreb_pct_rolling',
            'home_dreb_pct_rolling', 'away_dreb_pct_rolling',
            'home_elo', 'away_elo',
            'home_streak', 'away_streak',
            'home_home_win_rate', 'away_away_win_rate',
            'h2h_home_advantage',
            # Scores y diferencial
            'home_pts', 'away_pts', 'point_diff',
            # Diferenciales para entrenamiento
            'ppg_diff', 'net_rating_diff_rolling', 'pace_diff',
            'off_rating_diff', 'def_rating_diff', 'rest_days_diff', 'injuries_diff',
            # Diferenciales de boxscore actuales (tienen leakage, no usar en clasificación)
            'reb_diff', 'ast_diff', 'tov_diff',
            # Diferenciales rolling (sin leakage)
            'reb_rolling_diff', 'ast_rolling_diff', 'tov_rolling_diff', 'win_rate_diff',
            # Nuevos diferenciales v2
            'efg_pct_diff', 'tov_rate_diff', 'oreb_pct_diff', 'dreb_pct_diff',
            'elo_diff', 'streak_diff', 'home_away_split_diff',
        ]
        
        # Ensure target columns are populated from the dataframe
        # Note: 'ml' dataframe comes from ml_ready_games. We need to ensure we have the target values.
        # 'tt_home' and 'tt_away' have 'pts' and 'tov' (boxscore stats for THIS game).
        # We need to map them to home_pts, away_pts, home_to, away_to.
        
        # Re-merge target stats (pts, tov, net_rating) from tt to ml to ensure we have the actual game stats
        target_home = tt[tt['is_home'] == True][['game_id', 'pts', 'tov', 'net_rating']].rename(columns={'pts': 'home_pts_target', 'tov': 'home_to_target', 'net_rating': 'net_rating_diff_target'})
        target_away = tt[tt['is_home'] == False][['game_id', 'pts', 'tov']].rename(columns={'pts': 'away_pts_target', 'tov': 'away_to_target'})
        
        ml = ml.merge(target_home, on='game_id', how='left')
        ml = ml.merge(target_away, on='game_id', how='left')
        
        # Update target columns
        ml['home_pts'] = ml['home_pts_target']
        ml['away_pts'] = ml['away_pts_target']
        ml['home_to'] = ml['home_to_target']
        ml['away_to'] = ml['away_to_target']
        ml['point_diff'] = ml['home_pts'] - ml['away_pts']
        # net_rating_diff calculation from home team perspective (it's already diff in build_features logic)
        ml['net_rating_diff'] = ml['net_rating_diff_target']
        
        # Drop temp columns
        ml = ml.drop(columns=['home_pts_target', 'away_pts_target', 'home_to_target', 'away_to_target', 'net_rating_diff_target'])

        # Ensure all columns exist
        for c in final_cols:
            if c not in ml.columns:
                print(f"Adding missing column {c} with nulls")
                ml[c] = None
        
        # Add net_rating_diff to final_cols explicitly (it was missing from previous list or just passed through)
        if 'net_rating_diff' not in final_cols:
            final_cols.append('net_rating_diff')

        ml_final = ml[final_cols].copy()
        
        # Agregar columnas nuevas a la tabla si no existen
        new_columns_ddl = [
            ("home_reb_rolling",   "FLOAT"),
            ("away_reb_rolling",   "FLOAT"),
            ("home_ast_rolling",   "FLOAT"),
            ("away_ast_rolling",   "FLOAT"),
            ("home_tov_rolling",   "FLOAT"),
            ("away_tov_rolling",   "FLOAT"),
            ("home_win_rate_last10", "FLOAT"),
            ("away_win_rate_last10", "FLOAT"),
            ("reb_rolling_diff",   "FLOAT"),
            ("ast_rolling_diff",   "FLOAT"),
            ("tov_rolling_diff",   "FLOAT"),
            ("win_rate_diff",      "FLOAT"),
            # Nuevas columnas v2
            ("home_efg_pct_rolling", "FLOAT"),
            ("away_efg_pct_rolling", "FLOAT"),
            ("home_tov_rate_rolling", "FLOAT"),
            ("away_tov_rate_rolling", "FLOAT"),
            ("home_oreb_pct_rolling", "FLOAT"),
            ("away_oreb_pct_rolling", "FLOAT"),
            ("home_dreb_pct_rolling", "FLOAT"),
            ("away_dreb_pct_rolling", "FLOAT"),
            ("home_elo",           "FLOAT"),
            ("away_elo",           "FLOAT"),
            ("home_streak",        "FLOAT"),
            ("away_streak",        "FLOAT"),
            ("home_home_win_rate", "FLOAT"),
            ("away_away_win_rate", "FLOAT"),
            ("h2h_home_advantage", "FLOAT"),
            ("efg_pct_diff",       "FLOAT"),
            ("tov_rate_diff",      "FLOAT"),
            ("oreb_pct_diff",      "FLOAT"),
            ("dreb_pct_diff",      "FLOAT"),
            ("elo_diff",           "FLOAT"),
            ("streak_diff",        "FLOAT"),
            ("home_away_split_diff", "FLOAT"),
        ]
        with engine.begin() as conn:
            for col_name, col_type in new_columns_ddl:
                try:
                    conn.execute(text(
                        f"ALTER TABLE {ml_schema}.ml_ready_games ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                    ))
                except Exception:
                    pass  # columna ya existe

        # Crear tabla temporal y actualizar
        ml_final.to_sql('ml_ready_games_temp', engine, schema=ml_schema, if_exists='replace', index=False)

        with engine.begin() as conn:
            update_query = text(f"""
                UPDATE {ml_schema}.ml_ready_games m
                SET
                    home_ppg_last5 = t.home_ppg_last5,
                    away_ppg_last5 = t.away_ppg_last5,
                    home_net_rating_last10 = t.home_net_rating_last10,
                    away_net_rating_last10 = t.away_net_rating_last10,

                    home_rest_days = t.home_rest_days,
                    away_rest_days = t.away_rest_days,
                    home_injuries_count = t.home_injuries_count,
                    away_injuries_count = t.away_injuries_count,
                    home_b2b = t.home_b2b,
                    away_b2b = t.away_b2b,

                    home_pace_rolling = t.home_pace_rolling,
                    away_pace_rolling = t.away_pace_rolling,
                    home_off_rating_rolling = t.home_off_rating_rolling,
                    away_off_rating_rolling = t.away_off_rating_rolling,
                    home_def_rating_rolling = t.home_def_rating_rolling,
                    away_def_rating_rolling = t.away_def_rating_rolling,

                    home_fg_pct = t.home_fg_pct,
                    away_fg_pct = t.away_fg_pct,
                    home_3p_pct = t.home_3p_pct,
                    away_3p_pct = t.away_3p_pct,
                    home_ft_pct = t.home_ft_pct,
                    away_ft_pct = t.away_ft_pct,
                    home_reb = t.home_reb,
                    away_reb = t.away_reb,
                    home_ast = t.home_ast,
                    away_ast = t.away_ast,
                    home_stl = t.home_stl,
                    away_stl = t.away_stl,
                    home_blk = t.home_blk,
                    away_blk = t.away_blk,
                    home_to = t.home_to,
                    away_to = t.away_to,

                    home_reb_rolling = t.home_reb_rolling,
                    away_reb_rolling = t.away_reb_rolling,
                    home_ast_rolling = t.home_ast_rolling,
                    away_ast_rolling = t.away_ast_rolling,
                    home_tov_rolling = t.home_tov_rolling,
                    away_tov_rolling = t.away_tov_rolling,
                    home_win_rate_last10 = t.home_win_rate_last10,
                    away_win_rate_last10 = t.away_win_rate_last10,

                    home_pts = t.home_pts,
                    away_pts = t.away_pts,
                    point_diff = t.point_diff,
                    net_rating_diff = t.net_rating_diff,

                    ppg_diff = t.ppg_diff,
                    net_rating_diff_rolling = t.net_rating_diff_rolling,
                    pace_diff = t.pace_diff,
                    off_rating_diff = t.off_rating_diff,
                    def_rating_diff = t.def_rating_diff,
                    rest_days_diff = t.rest_days_diff,
                    injuries_diff = t.injuries_diff,
                    reb_diff = t.reb_diff,
                    ast_diff = t.ast_diff,
                    tov_diff = t.tov_diff,
                    reb_rolling_diff = t.reb_rolling_diff,
                    ast_rolling_diff = t.ast_rolling_diff,
                    tov_rolling_diff = t.tov_rolling_diff,
                    win_rate_diff = t.win_rate_diff,

                    home_efg_pct_rolling = t.home_efg_pct_rolling,
                    away_efg_pct_rolling = t.away_efg_pct_rolling,
                    home_tov_rate_rolling = t.home_tov_rate_rolling,
                    away_tov_rate_rolling = t.away_tov_rate_rolling,
                    home_oreb_pct_rolling = t.home_oreb_pct_rolling,
                    away_oreb_pct_rolling = t.away_oreb_pct_rolling,
                    home_dreb_pct_rolling = t.home_dreb_pct_rolling,
                    away_dreb_pct_rolling = t.away_dreb_pct_rolling,
                    home_elo = t.home_elo,
                    away_elo = t.away_elo,
                    home_streak = t.home_streak,
                    away_streak = t.away_streak,
                    home_home_win_rate = t.home_home_win_rate,
                    away_away_win_rate = t.away_away_win_rate,
                    h2h_home_advantage = t.h2h_home_advantage,
                    efg_pct_diff = t.efg_pct_diff,
                    tov_rate_diff = t.tov_rate_diff,
                    oreb_pct_diff = t.oreb_pct_diff,
                    dreb_pct_diff = t.dreb_pct_diff,
                    elo_diff = t.elo_diff,
                    streak_diff = t.streak_diff,
                    home_away_split_diff = t.home_away_split_diff
                FROM {ml_schema}.ml_ready_games_temp t
                WHERE m.game_id = t.game_id
            """)
            conn.execute(update_query)
            conn.execute(text(f"DROP TABLE IF EXISTS {ml_schema}.ml_ready_games_temp"))
        
        print("[OK] Features construidas y tabla ml_ready_games actualizada.")

        # Delete unused table
        print("[>] Eliminando tabla espn.team_stats_game (no utilizada)...")
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {espn_schema}.team_stats_game"))
        print("[OK] Tabla espn.team_stats_game eliminada.")
        
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    build_features()
