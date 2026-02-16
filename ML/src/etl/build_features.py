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
    print("🔧 FASE 2: Feature Engineering Básico y Rolling Features")
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
        
        print("📥 Paso 1: Cargando datos desde Neon...")
        print("-" * 60)
        
        # 1) Cargar games y otras tablas necesarias
        print("   Cargando espn.games...")
        games = pd.read_sql(
            f"SELECT * FROM {espn_schema}.games ORDER BY fecha",
            engine
        )
        print(f"   ✅ {len(games)} partidos cargados")
        
        print("   Cargando espn.game_id_mapping...")
        try:
            mapping = pd.read_sql(
                f"SELECT espn_id, nba_id FROM {espn_schema}.game_id_mapping",
                engine
            )
            # Normalizar tipos para join
            games['game_id_str'] = games['game_id'].astype(str)
            games = games.merge(mapping, left_on='game_id_str', right_on='espn_id', how='left')
            print(f"   ✅ Mapeo de IDs cargado y aplicado ({games['nba_id'].count()} coincidencias)")
        except Exception as e:
            print(f"   ⚠️  No se pudo cargar game_id_mapping: {e}")
            games['nba_id'] = None
        
        print("   Cargando espn.nba_player_boxscores...")
        try:
            player_box = pd.read_sql(
                f"SELECT game_id, team_tricode, pts, fga, fgm, fta, ftm, three_pa, three_pm, oreb, dreb, ast, stl, blk, to_stat as tov FROM {espn_schema}.nba_player_boxscores",
                engine
            )
            # COVERTIR game_id A BIGINT PARA MATCHING
            player_box['game_id'] = pd.to_numeric(player_box['game_id'], errors='coerce').astype('Int64')
            print(f"   ✅ {len(player_box)} registros loaded")
            
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
            print(f"   ✅ Estadísticas de equipo calculadas para {len(team_game_stats)} registros")
        except Exception as e:
            print(f"   ⚠️  No se pudo cargar o procesar nba_player_boxscores: {e}")
            print(e)
            team_game_stats = pd.DataFrame()
        
        print("   Cargando espn.injuries...")
        try:
            injuries = pd.read_sql(
                f"SELECT * FROM {espn_schema}.injuries",
                engine
            )
            print(f"   ✅ {len(injuries)} registros de lesiones cargados")
        except Exception as e:
            print(f"   ⚠️  No se pudo cargar injuries: {e}")
            injuries = pd.DataFrame()
        
        print("   Cargando espn.odds...")
        try:
            # En Neon, ml.ml_ready_games ya tiene las odds si usamos map_odds_to_games
            # pero aquí build_features calcula features adicionales
            odds = pd.read_sql(
                f"SELECT * FROM {espn_schema}.odds",
                engine
            )
            print(f"   ✅ {len(odds)} registros de cuotas cargados")
        except Exception as e:
            print(f"   ⚠️  No se pudo cargar odds: {e}")
            odds = pd.DataFrame()
        
        print()
        
        # 2) Normalizar nombres de equipos
        print("📝 Paso 2: Normalizando nombres de equipos...")
        print("-" * 60)
        
        # Mapeo de tricode a nombre de equipo si es necesario
        # (Aunque nba_player_boxscores usa tricode, games usa nombres completos)
        # Vamos a usar el mapping que ya existe en la base de datos si es posible
        print("   ✅ Usando nombres completos de equipos (no abreviaciones)")
        print()
        
        # 3) Helper: construir rolling aggregates por equipo
        print("📊 Paso 3: Calculando rolling features...")
        print("-" * 60)
        
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
                
                home_poss = home_stats.get('poss', None)
                away_poss = away_stats.get('poss', None)

                # Base Stats extraction
                def get_stat(stats, key, default=0):
                    return stats.get(key, default)
                
                # Rebounds
                h_oreb = get_stat(home_stats, 'oreb')
                h_dreb = get_stat(home_stats, 'dreb')
                h_reb = h_oreb + h_dreb
                
                a_oreb = get_stat(away_stats, 'oreb')
                a_dreb = get_stat(away_stats, 'dreb')
                a_reb = a_oreb + a_dreb
                
                # Assists, Steals, Blocks, TOV
                h_ast = get_stat(home_stats, 'ast')
                h_stl = get_stat(home_stats, 'stl')
                h_blk = get_stat(home_stats, 'blk')
                h_tov = get_stat(home_stats, 'tov')
                
                a_ast = get_stat(away_stats, 'ast')
                a_stl = get_stat(away_stats, 'stl')
                a_blk = get_stat(away_stats, 'blk')
                a_tov = get_stat(away_stats, 'tov')
                
                # Percentages
                h_fgm = get_stat(home_stats, 'fgm')
                h_fga = get_stat(home_stats, 'fga')
                h_fg_pct = (h_fgm / h_fga) if h_fga > 0 else 0.0
                
                a_fgm = get_stat(away_stats, 'fgm')
                a_fga = get_stat(away_stats, 'fga')
                a_fg_pct = (a_fgm / a_fga) if a_fga > 0 else 0.0
                
                h_fg3m = get_stat(home_stats, 'three_pm')
                h_fg3a = get_stat(home_stats, 'three_pa')
                h_fg3_pct = (h_fg3m / h_fg3a) if h_fg3a > 0 else 0.0
                
                a_fg3m = get_stat(away_stats, 'three_pm')
                a_fg3a = get_stat(away_stats, 'three_pa')
                a_fg3_pct = (a_fg3m / a_fg3a) if a_fg3a > 0 else 0.0
                
                h_ftm = get_stat(home_stats, 'ftm')
                h_fta = get_stat(home_stats, 'fta')
                h_ft_pct = (h_ftm / h_fta) if h_fta > 0 else 0.0
                
                a_ftm = get_stat(away_stats, 'ftm')
                a_fta = get_stat(away_stats, 'fta')
                a_ft_pct = (a_ftm / a_fta) if a_fta > 0 else 0.0
                
                # Si tenemos posesiones, calculamos ratings individuales de este partido
                home_off_rtg = (home_pts / home_poss * 100) if home_poss and home_poss > 0 else None
                away_off_rtg = (away_pts / away_poss * 100) if away_poss and away_poss > 0 else None
                
                # Pace (partido individual)
                game_pace = (home_poss + away_poss) / 2 if home_poss and away_poss else None
                
                rows.append({
                    'game_id': game_id,
                    'fecha': fecha,
                    'team': home_team,
                    'is_home': True,
                    'pts': home_pts,
                    'opp_pts': away_pts,
                    'net_rating': net_rating_diff,
                    'poss': home_poss,
                    'off_rtg': home_off_rtg,
                    'pace': game_pace,
                    'fg_pct': h_fg_pct, 'fg3_pct': h_fg3_pct, 'ft_pct': h_ft_pct,
                    'reb': h_reb, 'ast': h_ast, 'stl': h_stl, 'blk': h_blk, 'tov': h_tov
                })
                
                rows.append({
                    'game_id': game_id,
                    'fecha': fecha,
                    'team': away_team,
                    'is_home': False,
                    'pts': away_pts,
                    'opp_pts': home_pts,
                    'net_rating': -net_rating_diff,
                    'poss': away_poss,
                    'off_rtg': away_off_rtg,
                    'pace': game_pace,
                    'fg_pct': a_fg_pct, 'fg3_pct': a_fg3_pct, 'ft_pct': a_ft_pct,
                    'reb': a_reb, 'ast': a_ast, 'stl': a_stl, 'blk': a_blk, 'tov': a_tov
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
            
            return tt
        
        tt = rolling_stats(games, team_game_stats)
        print(f"   ✅ Rolling features calculadas para {len(tt)} registros")
        print()
        
        # 4) Merge rolling features back into ml_ready_games
        print("🔄 Paso 4: Aplicando rolling features a ml_ready_games...")
        print("-" * 60)
        
        # Leer ml_ready_games
        print("   Cargando ml_ready_games...")
        ml = pd.read_sql(
            f"SELECT * FROM {ml_schema}.ml_ready_games",
            engine
        )
        print(f"   ✅ {len(ml)} registros cargados")
        
        # Merge tt with ml
        tt_home = tt[tt['is_home'] == True].rename(columns={
            'pts_last5': 'home_ppg_last5',
            'net_last10': 'home_net_rating_last10',
            'pace_last5': 'home_pace_rolling',
            'off_rtg_last5': 'home_off_rating_rolling',
            'def_rtg_last5': 'home_def_rating_rolling',
            'fg_pct': 'home_fg_pct', 'fg3_pct': 'home_3p_pct', 'ft_pct': 'home_ft_pct',
            'reb': 'home_reb', 'ast': 'home_ast', 'stl': 'home_stl', 'blk': 'home_blk', 'tov': 'home_to'
        })[['game_id', 'home_ppg_last5', 'home_net_rating_last10', 'home_pace_rolling', 'home_off_rating_rolling', 'home_def_rating_rolling',
            'home_fg_pct', 'home_3p_pct', 'home_ft_pct', 'home_reb', 'home_ast', 'home_stl', 'home_blk', 'home_to']]
        
        tt_away = tt[tt['is_home'] == False].rename(columns={
            'pts_last5': 'away_ppg_last5',
            'net_last10': 'away_net_rating_last10',
            'pace_last5': 'away_pace_rolling',
            'off_rtg_last5': 'away_off_rating_rolling',
            'def_rtg_last5': 'away_def_rating_rolling',
            'fg_pct': 'away_fg_pct', 'fg3_pct': 'away_3p_pct', 'ft_pct': 'away_ft_pct',
            'reb': 'away_reb', 'ast': 'away_ast', 'stl': 'away_stl', 'blk': 'away_blk', 'tov': 'away_to'
        })[['game_id', 'away_ppg_last5', 'away_net_rating_last10', 'away_pace_rolling', 'away_off_rating_rolling', 'away_def_rating_rolling',
            'away_fg_pct', 'away_3p_pct', 'away_ft_pct', 'away_reb', 'away_ast', 'away_stl', 'away_blk', 'away_to']]
        
        # Limpiar ml de columnas que vamos a sobreescribir para evitar duplicados en el merge
        cols_to_drop = ['home_ppg_last5', 'away_ppg_last5', 'home_net_rating_last10', 'away_net_rating_last10',
                        'home_pace_rolling', 'away_pace_rolling', 'home_off_rating_rolling', 'away_off_rating_rolling',
                        'home_def_rating_rolling', 'away_def_rating_rolling',
                        'home_fg_pct', 'home_3p_pct', 'home_ft_pct', 'home_reb', 'home_ast', 'home_stl', 'home_blk', 'home_to',
                        'away_fg_pct', 'away_3p_pct', 'away_ft_pct', 'away_reb', 'away_ast', 'away_stl', 'away_blk', 'away_to']
        ml = ml.drop(columns=[c for c in cols_to_drop if c in ml.columns])
        
        ml = ml.merge(tt_home, on='game_id', how='left')
        ml = ml.merge(tt_away, on='game_id', how='left')
        
        print("   ✅ Rolling features aplicadas")
        print()
        
        # 5) Rest days and B2B
        print("📅 Paso 5: Calculando días de descanso y B2B...")
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
        
        print(f"   ✅ Días de descanso y B2B calculados")
        print()
        
        # 6) Contar lesiones
        print("🏥 Paso 6: Contando lesiones...")
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
        print("🧮 Paso 7: Calculando diferenciales finales...")
        print("-" * 60)
        
        ml['ppg_diff'] = ml['home_ppg_last5'] - ml['away_ppg_last5']
        ml['net_rating_diff_rolling'] = ml['home_net_rating_last10'] - ml['away_net_rating_last10']
        ml['pace_diff'] = ml['home_pace_rolling'] - ml['away_pace_rolling']
        ml['off_rating_diff'] = ml['home_off_rating_rolling'] - ml['away_off_rating_rolling']
        ml['def_rating_diff'] = ml['home_def_rating_rolling'] - ml['away_def_rating_rolling']
        
        # Base Stat Differentials
        ml['reb_diff'] = ml['home_reb'] - ml['away_reb']
        ml['ast_diff'] = ml['home_ast'] - ml['away_ast']
        ml['tov_diff'] = ml['home_to'] - ml['away_to']
        # Also could enable others if column exists in table (e.g. stl_diff) but sticking to schema for now
        ml['rest_days_diff'] = (ml['home_rest_days'].fillna(3) - ml['away_rest_days'].fillna(3)).astype(int)
        ml['injuries_diff'] = ml['home_injuries_count'] - ml['away_injuries_count']
        
        print("   ✅ Diferenciales calculados")
        print()
        
        # 8) Odds Probs (si no están ya mapeadas)
        # Probabilidades implícitas si existen
        # (Omitimos el mapeo JSON manual si ya está en espn.game_odds)
        
        # Escribir a BD
        print("💾 Paso 8: Actualizando ml_ready_games en Neon...")
        print("-" * 60)
        
        # Seleccionar columnas finales
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
            'home_ft_pct', 'away_ft_pct', 'home_reb', 'away_reb',
            'home_ast', 'away_ast', 'home_stl', 'away_stl',
            'home_blk', 'away_blk', 'home_to', 'away_to',
            'home_pts', 'away_pts', 'point_diff',
            'ppg_diff', 'net_rating_diff_rolling', 'pace_diff',
            'off_rating_diff', 'def_rating_diff', 'rest_days_diff', 'injuries_diff',
            'reb_diff', 'ast_diff', 'tov_diff'
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
        
        # Crear tabla temporal y actualizar
        temp_table = f"{ml_schema}.ml_ready_games_temp"
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
                    tov_diff = t.tov_diff
                FROM {ml_schema}.ml_ready_games_temp t
                WHERE m.game_id = t.game_id
            """)
            conn.execute(update_query)
            conn.execute(text(f"DROP TABLE IF EXISTS {ml_schema}.ml_ready_games_temp"))
        
        print("✅ Features construidas y tabla ml_ready_games actualizada.")

        # Delete unused table
        print("🗑️ Eliminando tabla espn.team_stats_game (no utilizada)...")
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {espn_schema}.team_stats_game"))
        print("✅ Tabla espn.team_stats_game eliminada.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    build_features()
