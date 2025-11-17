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
        
        print("   Cargando espn.team_stats...")
        try:
            team_stats = pd.read_sql(
                f"SELECT * FROM {espn_schema}.team_stats ORDER BY game_id, team_id",
                engine
            )
            print(f"   ✅ {len(team_stats)} registros de estadísticas de equipos cargados")
        except Exception as e:
            print(f"   ⚠️  No se pudo cargar team_stats: {e}")
            team_stats = pd.DataFrame()
        
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
        # IMPORTANTE: ml_ready_games usa nombres completos, no abreviaciones
        print("📝 Paso 2: Normalizando nombres de equipos...")
        print("-" * 60)
        
        # Usar nombres completos (home_team, away_team) en lugar de normalized
        # porque ml_ready_games usa nombres completos
        games['home_team_norm'] = games['home_team']
        games['away_team_norm'] = games['away_team']
        print("   ✅ Usando nombres completos de equipos (no abreviaciones)")
        print()
        
        # 3) Helper: construir rolling aggregates por equipo
        print("📊 Paso 3: Calculando rolling features...")
        print("-" * 60)
        
        def rolling_stats(df_games):
            """
            Construye estadísticas rolling por equipo
            """
            rows = []
            
            for _, r in tqdm(df_games.iterrows(), total=len(df_games), desc="   Procesando partidos"):
                game_id = r['game_id']
                home_team = r['home_team_norm']
                away_team = r['away_team_norm']
                fecha = pd.to_datetime(r['fecha'])
                
                # Obtener puntos y net rating
                home_pts = r.get('home_pts', r.get('home_score', 0))
                away_pts = r.get('away_pts', r.get('away_score', 0))
                
                # Net rating: diferencia de puntos (simplificado)
                net_rating_diff = r.get('net_rating_diff', 0)
                if pd.isna(net_rating_diff):
                    net_rating_diff = 0
                
                rows.append({
                    'game_id': game_id,
                    'fecha': fecha,
                    'team': home_team,
                    'is_home': True,
                    'pts': home_pts,
                    'net_rating': net_rating_diff
                })
                
                rows.append({
                    'game_id': game_id,
                    'fecha': fecha,
                    'team': away_team,
                    'is_home': False,
                    'pts': away_pts,
                    'net_rating': -net_rating_diff  # Negativo para el visitante
                })
            
            tt = pd.DataFrame(rows).sort_values(['team', 'fecha', 'game_id'])
            
            # Rolling 5 partidos para puntos
            print("   Calculando PPG últimos 5 partidos...")
            tt['pts_last5'] = tt.groupby('team')['pts'].transform(
                lambda x: x.rolling(window=5, min_periods=1).mean()
            )
            
            # Rolling 10 partidos para net rating
            print("   Calculando Net Rating últimos 10 partidos...")
            tt['net_last10'] = tt.groupby('team')['net_rating'].transform(
                lambda x: x.rolling(window=10, min_periods=1).mean()
            )
            
            return tt
        
        tt = rolling_stats(games)
        print(f"   ✅ Rolling features calculadas para {len(tt)} registros")
        print()
        
        # 4) Merge rolling features back into ml_ready_games
        print("🔄 Paso 4: Aplicando rolling features a ml_ready_games...")
        print("-" * 60)
        
        # Crear mapeo: (game_id, team) -> pts_last5, net_last10
        map_last5 = tt.set_index(['game_id', 'team'])['pts_last5'].to_dict()
        map_net10 = tt.set_index(['game_id', 'team'])['net_last10'].to_dict()
        
        # Leer ml_ready_games
        print("   Cargando ml_ready_games...")
        ml = pd.read_sql(
            f"SELECT * FROM {ml_schema}.ml_ready_games",
            engine
        )
        print(f"   ✅ {len(ml)} registros cargados")
        
        # Aplicar features
        print("   Aplicando rolling features...")
        def get_feat(game_row):
            gid = game_row['game_id']
            home = game_row.get('home_team', game_row.get('home_team_norm'))
            away = game_row.get('away_team', game_row.get('away_team_norm'))
            
            r = {}
            r['home_ppg_last5'] = map_last5.get((gid, home), None)
            r['away_ppg_last5'] = map_last5.get((gid, away), None)
            r['home_net_rating_last10'] = map_net10.get((gid, home), None)
            r['away_net_rating_last10'] = map_net10.get((gid, away), None)
            return pd.Series(r)
        
        feat_df = ml.apply(get_feat, axis=1)
        ml[['home_ppg_last5', 'away_ppg_last5', 'home_net_rating_last10', 'away_net_rating_last10']] = feat_df
        print("   ✅ Rolling features aplicadas")
        print()
        
        # 5) Rest days (diferencia entre fecha actual y último partido de cada equipo)
        print("📅 Paso 5: Calculando días de descanso...")
        print("-" * 60)
        
        games_dates = games[['game_id', 'fecha', 'home_team_norm', 'away_team_norm']].copy()
        games_dates['fecha'] = pd.to_datetime(games_dates['fecha'])
        games_dates = games_dates.sort_values('fecha')
        
        # Construir última fecha de partido por equipo
        last_dates = {}
        rest_home = []
        rest_away = []
        
        for _, row in tqdm(games_dates.iterrows(), total=len(games_dates), desc="   Calculando rest days"):
            gid = row['game_id']
            home = row['home_team_norm']
            away = row['away_team_norm']
            date = row['fecha']
            
            last_home = last_dates.get(home, None)
            last_away = last_dates.get(away, None)
            
            rest_home.append((date - last_home).days if last_home is not None else None)
            rest_away.append((date - last_away).days if last_away is not None else None)
            
            last_dates[home] = date
            last_dates[away] = date
        
        # Crear DataFrame temporal para merge
        rest_df = pd.DataFrame({
            'game_id': games_dates['game_id'].values,
            'home_rest_days': rest_home,
            'away_rest_days': rest_away
        })
        
        # Convertir NaN a None para que se manejen correctamente
        rest_df['home_rest_days'] = rest_df['home_rest_days'].where(pd.notna(rest_df['home_rest_days']), None)
        rest_df['away_rest_days'] = rest_df['away_rest_days'].where(pd.notna(rest_df['away_rest_days']), None)
        
        # Asegurarse de que ml tenga game_id como columna (no índice)
        if 'game_id' not in ml.columns:
            ml = ml.reset_index()
        
        # Hacer merge asegurando que los tipos de game_id coincidan
        rest_df['game_id'] = rest_df['game_id'].astype(ml['game_id'].dtype)
        ml = ml.merge(rest_df, on='game_id', how='left')
        
        # Si el merge no funcionó, intentar asignar directamente
        if 'home_rest_days_x' in ml.columns or 'home_rest_days_y' in ml.columns:
            # Hubo conflicto de nombres, usar los nuevos
            if 'home_rest_days_y' in ml.columns:
                ml['home_rest_days'] = ml['home_rest_days_y']
                ml['away_rest_days'] = ml['away_rest_days_y']
                ml = ml.drop(columns=['home_rest_days_x', 'away_rest_days_x', 'home_rest_days_y', 'away_rest_days_y'], errors='ignore')
        
        # Asegurarse de que las columnas existan
        if 'home_rest_days' not in ml.columns:
            ml['home_rest_days'] = None
        if 'away_rest_days' not in ml.columns:
            ml['away_rest_days'] = None
        
        # Verificar cuántos se aplicaron
        rest_applied = ml['home_rest_days'].notna().sum()
        print(f"   ✅ Días de descanso calculados ({rest_applied}/{len(ml)} aplicados)")
        print()
        
        # 6) Injuries count por equipo en la fecha del partido
        print("🏥 Paso 6: Contando lesiones...")
        print("-" * 60)
        
        if not injuries.empty:
            # Si hay columna de fecha, filtrar por fecha del partido
            if 'injury_date' in injuries.columns or 'date' in injuries.columns:
                date_col = 'injury_date' if 'injury_date' in injuries.columns else 'date'
                injuries[date_col] = pd.to_datetime(injuries[date_col], errors='coerce')
            
            # Mapear lesiones por equipo
            # Si hay columna 'team', usarla; si no, intentar otras
            team_col = None
            for col in ['team', 'team_name', 'team_id']:
                if col in injuries.columns:
                    team_col = col
                    break
            
            if team_col:
                # Contar lesiones activas por equipo (simplificado: todas las lesiones)
                inj_counts = injuries.groupby(team_col).size().to_dict()
                
                ml['home_injuries_count'] = ml['home_team'].map(
                    lambda t: inj_counts.get(t, 0) if pd.notna(t) else 0
                )
                ml['away_injuries_count'] = ml['away_team'].map(
                    lambda t: inj_counts.get(t, 0) if pd.notna(t) else 0
                )
                print(f"   ✅ Lesiones contadas para {len(inj_counts)} equipos")
            else:
                print("   ⚠️  No se encontró columna de equipo en injuries")
                ml['home_injuries_count'] = 0
                ml['away_injuries_count'] = 0
        else:
            print("   ⚠️  Tabla injuries vacía o no disponible")
            ml['home_injuries_count'] = 0
            ml['away_injuries_count'] = 0
        print()
        
        # 7) Implied probability desde tabla odds (JSON bookmakers)
        print("💰 Paso 7: Calculando probabilidades implícitas desde odds...")
        print("-" * 60)
        
        if not odds.empty and 'bookmakers' in odds.columns:
            try:
                import json
                
                def extract_implied_probs(row):
                    """
                    Extrae probabilidades implícitas desde bookmakers JSON
                    """
                    home_team = row.get('home_team')
                    away_team = row.get('away_team')
                    bookmakers = row.get('bookmakers')
                    
                    if not bookmakers:
                        return None, None
                    
                    # Parsear JSON si es string
                    if isinstance(bookmakers, str):
                        try:
                            bookmakers = json.loads(bookmakers)
                        except:
                            return None, None
                    
                    if not isinstance(bookmakers, list) or len(bookmakers) == 0:
                        return None, None
                    
                    # Usar el primer bookmaker disponible
                    # Buscar market "h2h" (head-to-head)
                    home_odds_list = []
                    away_odds_list = []
                    
                    for bookmaker in bookmakers:
                        if 'markets' not in bookmaker:
                            continue
                        
                        for market in bookmaker['markets']:
                            if market.get('key') != 'h2h':
                                continue
                            
                            if 'outcomes' not in market:
                                continue
                            
                            for outcome in market['outcomes']:
                                name = outcome.get('name', '')
                                price = outcome.get('price')
                                
                                if price and price > 0:
                                    # Intentar mapear por nombre de equipo (coincidencia flexible)
                                    name_lower = name.lower()
                                    if home_team:
                                        home_lower = home_team.lower()
                                        # Coincidencia exacta o parcial
                                        if (home_lower in name_lower or 
                                            name_lower in home_lower or
                                            any(word in name_lower for word in home_lower.split() if len(word) > 3)):
                                            home_odds_list.append(price)
                                    if away_team:
                                        away_lower = away_team.lower()
                                        # Coincidencia exacta o parcial
                                        if (away_lower in name_lower or 
                                            name_lower in away_lower or
                                            any(word in name_lower for word in away_lower.split() if len(word) > 3)):
                                            away_odds_list.append(price)
                    
                    # Calcular promedio de odds si hay múltiples
                    home_odds = np.mean(home_odds_list) if home_odds_list else None
                    away_odds = np.mean(away_odds_list) if away_odds_list else None
                    
                    # Calcular probabilidad implícita
                    home_prob = 1.0 / home_odds if home_odds and home_odds > 0 else None
                    away_prob = 1.0 / away_odds if away_odds and away_odds > 0 else None
                    
                    return home_prob, away_prob
                
                # Mapear odds por home_team y away_team (ya que game_id puede no coincidir)
                print("   Extrayendo probabilidades desde bookmakers JSON...")
                odds_probs = {}
                
                for _, odds_row in tqdm(odds.iterrows(), total=len(odds), desc="   Procesando odds"):
                    home_team = odds_row.get('home_team')
                    away_team = odds_row.get('away_team')
                    
                    if home_team and away_team:
                        home_prob, away_prob = extract_implied_probs(odds_row)
                        key = (home_team, away_team)
                        odds_probs[key] = (home_prob, away_prob)
                
                print(f"   ✅ {len(odds_probs)} partidos con odds procesados")
                
                # Aplicar a ml_ready_games con mapeo flexible
                def get_implied_prob_for_game(game_row):
                    home_team = game_row.get('home_team')
                    away_team = game_row.get('away_team')
                    
                    # Buscar coincidencia exacta primero
                    key = (home_team, away_team)
                    if key in odds_probs:
                        return pd.Series({
                            'implied_prob_home': odds_probs[key][0],
                            'implied_prob_away': odds_probs[key][1]
                        })
                    
                    # Buscar coincidencia flexible (solo home o away)
                    for (odds_home, odds_away), (home_prob, away_prob) in odds_probs.items():
                        home_match = (home_team and (
                            home_team.lower() in odds_home.lower() or 
                            odds_home.lower() in home_team.lower() or
                            any(word in odds_home.lower() for word in home_team.lower().split() if len(word) > 3)
                        ))
                        away_match = (away_team and (
                            away_team.lower() in odds_away.lower() or 
                            odds_away.lower() in away_team.lower() or
                            any(word in odds_away.lower() for word in away_team.lower().split() if len(word) > 3)
                        ))
                        
                        if home_match and away_match:
                            return pd.Series({
                                'implied_prob_home': home_prob,
                                'implied_prob_away': away_prob
                            })
                    
                    return pd.Series({
                        'implied_prob_home': None,
                        'implied_prob_away': None
                    })
                
                prob_df = ml.apply(get_implied_prob_for_game, axis=1)
                ml[['implied_prob_home', 'implied_prob_away']] = prob_df
                
                applied_count = ml['implied_prob_home'].notna().sum()
                print(f"   ✅ Probabilidades aplicadas a {applied_count} partidos")
                
            except Exception as e:
                print(f"   ⚠️  Error al calcular probabilidades: {e}")
                import traceback
                traceback.print_exc()
                ml['implied_prob_home'] = None
                ml['implied_prob_away'] = None
        else:
            print("   ⚠️  Tabla odds vacía o no tiene columna bookmakers")
            ml['implied_prob_home'] = None
            ml['implied_prob_away'] = None
        print()
        
        # 8) Escribir de vuelta a la BD: actualizar filas en ml.ml_ready_games
        print("💾 Paso 8: Actualizando ml_ready_games en la base de datos...")
        print("-" * 60)
        
        # Asegurarse de que todas las columnas necesarias existan
        required_cols = [
            'home_ppg_last5', 'away_ppg_last5', 
            'home_net_rating_last10', 'away_net_rating_last10',
            'home_rest_days', 'away_rest_days',
            'home_injuries_count', 'away_injuries_count',
            'implied_prob_home', 'implied_prob_away'
        ]
        
        for col in required_cols:
            if col not in ml.columns:
                ml[col] = None
                print(f"   ⚠️  Columna {col} no encontrada, se agregará como NULL")
        
        # Seleccionar solo las columnas que necesitamos actualizar + game_id
        update_cols = ['game_id'] + required_cols
        ml_update = ml[update_cols].copy()
        
        # Asegurar tipos de datos correctos
        # double precision columns
        float_cols = ['home_ppg_last5', 'away_ppg_last5', 
                     'home_net_rating_last10', 'away_net_rating_last10',
                     'implied_prob_home', 'implied_prob_away']
        for col in float_cols:
            if col in ml_update.columns:
                ml_update[col] = pd.to_numeric(ml_update[col], errors='coerce').astype('float64')
        
        # integer columns
        int_cols = ['home_rest_days', 'away_rest_days',
                   'home_injuries_count', 'away_injuries_count']
        for col in int_cols:
            if col in ml_update.columns:
                ml_update[col] = pd.to_numeric(ml_update[col], errors='coerce').astype('Int64')  # Nullable integer
        
        # Crear tabla temporal
        temp_table = f"{ml_schema}.ml_ready_games_temp"
        ml_update.to_sql(
            'ml_ready_games_temp',
            engine,
            schema=ml_schema,
            if_exists='replace',
            index=False
        )
        print("   ✅ Tabla temporal creada")
        
        # Verificar columnas en tabla temporal
        with engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {ml_schema}, public"))
            conn.commit()
            check_cols = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'ml' 
                AND table_name = 'ml_ready_games_temp'
                ORDER BY ordinal_position
            """))
            temp_cols = [row[0] for row in check_cols.fetchall()]
            print(f"   Columnas en tabla temporal: {', '.join(temp_cols[:10])}...")
        
        # Actualizar tabla principal con casts explícitos
        with engine.begin() as conn:
            update_query = text(f"""
                UPDATE {ml_schema}.ml_ready_games m
                SET 
                    home_ppg_last5 = t.home_ppg_last5::double precision,
                    away_ppg_last5 = t.away_ppg_last5::double precision,
                    home_net_rating_last10 = t.home_net_rating_last10::double precision,
                    away_net_rating_last10 = t.away_net_rating_last10::double precision,
                    home_rest_days = t.home_rest_days::integer,
                    away_rest_days = t.away_rest_days::integer,
                    home_injuries_count = t.home_injuries_count::integer,
                    away_injuries_count = t.away_injuries_count::integer,
                    implied_prob_home = t.implied_prob_home::double precision,
                    implied_prob_away = t.implied_prob_away::double precision
                FROM {ml_schema}.ml_ready_games_temp t
                WHERE m.game_id = t.game_id
            """)
            conn.execute(update_query)
            print("   ✅ Tabla ml_ready_games actualizada")
            
            # Eliminar tabla temporal
            conn.execute(text(f"DROP TABLE IF EXISTS {ml_schema}.ml_ready_games_temp"))
            print("   ✅ Tabla temporal eliminada")
        
        print()
        print("=" * 60)
        print("✅ Features construidas y actualizadas exitosamente")
        print("=" * 60)
        print()
        
        # Verificación
        print("📊 Verificación:")
        print("-" * 60)
        with engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {ml_schema}, public"))
            conn.commit()
            
            # Contar NULLs
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(home_ppg_last5) as with_ppg,
                    COUNT(home_rest_days) as with_rest,
                    COUNT(home_injuries_count) as with_injuries,
                    COUNT(implied_prob_home) as with_odds
                FROM ml.ml_ready_games
            """))
            row = result.fetchone()
            
            print(f"   Total de registros: {row[0]}")
            print(f"   Con PPG last 5: {row[1]} ({100*row[1]/row[0]:.1f}%)")
            print(f"   Con rest days: {row[2]} ({100*row[2]/row[0]:.1f}%)")
            print(f"   Con injuries count: {row[3]} ({100*row[3]/row[0]:.1f}%)")
            print(f"   Con implied prob: {row[4]} ({100*row[4]/row[0]:.1f}%)")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    build_features()

