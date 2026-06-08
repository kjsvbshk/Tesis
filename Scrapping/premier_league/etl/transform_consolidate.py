#!/usr/bin/env python3
"""
ETL para consolidar datos de Premier League.
Consolida partidos duplicados (cada partido aparece 2 veces, una por cada equipo)
en un solo registro por partido.
"""

import os
import pandas as pd
from pathlib import Path
from loguru import logger
import sys

# Agregar utils al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

# Configurar logger
setup_logger()


def consolidate_matches_by_game(df):
    """
    Consolidar partidos duplicados en un solo registro por partido.
    
    Cada partido aparece 2 veces (una vez por cada equipo). Esta función
    crea un solo registro con home_team, away_team, home_score, away_score.
    
    Args:
        df (pd.DataFrame): DataFrame con partidos duplicados
    
    Returns:
        pd.DataFrame: DataFrame consolidado con un registro por partido
    """
    logger.info("Consolidando partidos duplicados...")
    
    # Crear identificador único por partido (date + equipos)
    # Ordenar equipos alfabéticamente para que sea consistente
    df['team_pair'] = df.apply(
        lambda row: tuple(sorted([row['team_name'], row['opponent']])),
        axis=1
    )
    
    # Agregar fecha al identificador
    df['match_id'] = df['date'].astype(str) + '_' + df['team_pair'].astype(str)
    
    # Agrupar por match_id y consolidar
    consolidated_matches = []
    processed_ids = set()
    
    for match_id, group in df.groupby('match_id'):
        if match_id in processed_ids:
            continue
        
        if len(group) < 2:
            # Solo hay un registro, usar ese
            row = group.iloc[0]
            if row['venue'] == 'Home':
                home_team = row['team_name']
                away_team = row['opponent']
                home_score = row['goals_for']
                away_score = row['goals_against']
            else:
                home_team = row['opponent']
                away_team = row['team_name']
                home_score = row['goals_against']
                away_score = row['goals_for']
            
            consolidated_matches.append({
                'match_id': match_id,
                'season': row['season'],
                'date': row['date'],
                'home_team': home_team,
                'away_team': away_team,
                'home_score': home_score,
                'away_score': away_score,
                'status': row['status'],
                'competition': row['competition']
            })
        else:
            # Hay 2 registros (uno por cada equipo), consolidar
            row1 = group.iloc[0]
            row2 = group.iloc[1]
            
            # Determinar cuál es home y cuál es away
            if row1['venue'] == 'Home':
                home_row = row1
                away_row = row2
            elif row2['venue'] == 'Home':
                home_row = row2
                away_row = row1
            else:
                # Si ambos son Away (caso raro), usar el primero como home
                logger.warning(f"Ambos registros son Away para match_id {match_id}, usando primero como home")
                home_row = row1
                away_row = row2
            
            # Verificar que los equipos coincidan
            if home_row['team_name'] != away_row['opponent'] or away_row['team_name'] != home_row['opponent']:
                logger.warning(f"Equipos no coinciden para match_id {match_id}: {home_row['team_name']} vs {away_row['team_name']}")
            
            # Verificar que los marcadores coincidan
            if home_row['goals_for'] != away_row['goals_against'] or away_row['goals_for'] != home_row['goals_against']:
                logger.warning(f"Marcadores no coinciden para match_id {match_id}")
            
            consolidated_matches.append({
                'match_id': match_id,
                'season': home_row['season'],
                'date': home_row['date'],
                'home_team': home_row['team_name'],
                'away_team': away_row['team_name'],
                'home_score': home_row['goals_for'],
                'away_score': away_row['goals_for'],
                'status': home_row['status'],
                'competition': home_row['competition']
            })
        
        processed_ids.add(match_id)
    
    df_consolidated = pd.DataFrame(consolidated_matches)
    
    # Calcular variables derivadas
    df_consolidated = calculate_derived_variables(df_consolidated)
    
    logger.info(f"Partidos consolidados: {len(df)} registros → {len(df_consolidated)} partidos únicos")
    
    return df_consolidated


def calculate_derived_variables(df):
    """
    Calcular variables derivadas.
    
    Args:
        df (pd.DataFrame): DataFrame con partidos consolidados
    
    Returns:
        pd.DataFrame: DataFrame con variables derivadas
    """
    logger.info("Calculando variables derivadas...")
    
    # home_win: 1 si gana el equipo local, 0 si no
    df['home_win'] = (df['home_score'] > df['away_score']).astype(int)
    
    # goal_diff: diferencia de goles (local - visitante)
    df['goal_diff'] = df['home_score'] - df['away_score']
    
    # total_goals: total de goles en el partido
    df['total_goals'] = df['home_score'] + df['away_score']
    
    logger.info("Variables derivadas calculadas")
    
    return df


def read_matches_data():
    """
    Leer todos los archivos CSV de partidos desde data/raw/.
    
    Returns:
        pd.DataFrame: DataFrame con todos los partidos
    """
    raw_dir = Path("data/raw")
    
    if not raw_dir.exists():
        logger.warning(f"Directorio {raw_dir} no existe")
        return None
    
    # Buscar todos los archivos CSV de Premier League (diferentes formatos de nombre)
    csv_files = list(raw_dir.glob("premier_league*.csv"))
    
    if not csv_files:
        logger.warning("No se encontraron archivos CSV de partidos")
        return None
    
    logger.info(f"Leyendo {len(csv_files)} archivos CSV...")
    
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
            logger.info(f"  → {csv_file.name}: {len(df)} registros")
        except Exception as e:
            logger.error(f"Error al leer {csv_file.name}: {e}")
            continue
    
    if not dfs:
        return None
    
    # Combinar todos los DataFrames
    df_combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total de registros combinados: {len(df_combined)}")
    
    return df_combined


def clean_dataset(df):
    """
    Limpiar dataset: eliminar duplicados y normalizar tipos.
    
    Args:
        df (pd.DataFrame): Dataset a limpiar
    
    Returns:
        pd.DataFrame: Dataset limpio
    """
    logger.info("Limpiando dataset...")
    
    initial_rows = len(df)
    
    # Eliminar duplicados por match_id
    df = df.drop_duplicates(subset=['match_id'], keep='first')
    
    # Normalizar tipos de datos
    numeric_columns = ['home_score', 'away_score', 'home_win', 'goal_diff', 'total_goals']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Eliminar filas con valores críticos faltantes
    critical_columns = ['date', 'home_team', 'away_team', 'home_score', 'away_score']
    df = df.dropna(subset=critical_columns)
    
    final_rows = len(df)
    removed_rows = initial_rows - final_rows
    
    logger.info(f"Dataset limpio: {removed_rows} filas eliminadas, {final_rows} filas restantes")
    
    return df


def save_consolidated_dataset(df):
    """
    Guardar dataset consolidado.
    
    Args:
        df (pd.DataFrame): Dataset consolidado
    """
    try:
        # Crear directorio si no existe
        os.makedirs("data/processed", exist_ok=True)
        
        # Guardar CSV
        output_path = "data/processed/premier_league_full_dataset.csv"
        df.to_csv(output_path, index=False)
        
        logger.info(f"Dataset consolidado guardado en {output_path}")
        logger.info(f"Dimensiones del dataset: {df.shape}")
        logger.info(f"Columnas: {list(df.columns)}")
        
    except Exception as e:
        logger.error(f"Error al guardar dataset consolidado: {e}")


def read_standings_data():
    """Leer datos de clasificaciones desde data/raw/standings/"""
    standings_dir = Path("data/raw/standings")
    
    if not standings_dir.exists():
        logger.warning(f"Directorio {standings_dir} no existe")
        return None
    
    csv_files = list(standings_dir.glob("*.csv"))
    if not csv_files:
        logger.warning("No se encontraron archivos CSV de clasificaciones")
        return None
    
    logger.info(f"Leyendo {len(csv_files)} archivos de clasificaciones...")
    
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
            logger.info(f"  → {csv_file.name}: {len(df)} registros")
        except Exception as e:
            logger.error(f"Error al leer {csv_file.name}: {e}")
            continue
    
    if not dfs:
        return None
    
    df_combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total de registros de clasificaciones: {len(df_combined)}")
    
    return df_combined


def read_team_stats_data():
    """Leer datos de estadísticas de equipos desde data/raw/team_stats/"""
    team_stats_dir = Path("data/raw/team_stats")
    
    if not team_stats_dir.exists():
        logger.warning(f"Directorio {team_stats_dir} no existe")
        return None
    
    csv_files = list(team_stats_dir.glob("*.csv"))
    if not csv_files:
        logger.warning("No se encontraron archivos CSV de estadísticas de equipos")
        return None
    
    logger.info(f"Leyendo {len(csv_files)} archivos de estadísticas de equipos...")
    
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
            logger.info(f"  → {csv_file.name}: {len(df)} registros")
        except Exception as e:
            logger.error(f"Error al leer {csv_file.name}: {e}")
            continue
    
    if not dfs:
        return None
    
    df_combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total de registros de estadísticas de equipos: {len(df_combined)}")
    
    return df_combined


def read_match_stats_data():
    """Leer datos de estadísticas detalladas de partidos desde data/raw/match_stats/"""
    match_stats_dir = Path("data/raw/match_stats")
    
    if not match_stats_dir.exists():
        logger.warning(f"Directorio {match_stats_dir} no existe")
        return None
    
    csv_files = list(match_stats_dir.glob("*.csv"))
    if not csv_files:
        logger.warning("No se encontraron archivos CSV de estadísticas de partidos")
        return None
    
    logger.info(f"Leyendo {len(csv_files)} archivos de estadísticas de partidos...")
    
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
            logger.info(f"  → {csv_file.name}: {len(df)} registros")
        except Exception as e:
            logger.error(f"Error al leer {csv_file.name}: {e}")
            continue
    
    if not dfs:
        return None
    
    df_combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total de registros de estadísticas de partidos: {len(df_combined)}")
    
    return df_combined


def read_player_stats_data():
    """Leer datos de estadísticas de jugadores desde data/raw/player_stats/"""
    player_stats_dir = Path("data/raw/player_stats")
    
    if not player_stats_dir.exists():
        logger.warning(f"Directorio {player_stats_dir} no existe")
        return None
    
    csv_files = list(player_stats_dir.glob("*.csv"))
    if not csv_files:
        logger.warning("No se encontraron archivos CSV de estadísticas de jugadores")
        return None
    
    logger.info(f"Leyendo {len(csv_files)} archivos de estadísticas de jugadores...")
    
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
            logger.info(f"  → {csv_file.name}: {len(df)} registros")
        except Exception as e:
            logger.error(f"Error al leer {csv_file.name}: {e}")
            continue
    
    if not dfs:
        return None
    
    df_combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total de registros de estadísticas de jugadores: {len(df_combined)}")
    
    return df_combined


def consolidate_premier_league_data():
    """
    Consolidar todos los datos de Premier League.
    
    Returns:
        pd.DataFrame: Dataset consolidado
    """
    logger.info("=== INICIANDO CONSOLIDACION DE DATOS PREMIER LEAGUE ===")
    
    try:
        # Leer datos principales (matches)
        df_matches = read_matches_data()
        
        if df_matches is None:
            logger.error("No se pudieron leer los datos de partidos")
            return None
        
        # Consolidar partidos duplicados
        df_consolidated = consolidate_matches_by_game(df_matches)
        
        # Leer y combinar datos adicionales si existen
        df_match_stats = read_match_stats_data()
        if df_match_stats is not None:
            # Combinar estadísticas detalladas de partidos
            df_consolidated = df_consolidated.merge(
                df_match_stats,
                on='match_id',
                how='left',
                suffixes=('', '_stats')
            )
            logger.info("Estadísticas detalladas de partidos combinadas")
        
        # Limpiar datos
        df_consolidated = clean_dataset(df_consolidated)
        
        # Guardar dataset final
        save_consolidated_dataset(df_consolidated)
        
        logger.info("=== CONSOLIDACION COMPLETADA EXITOSAMENTE ===")
        return df_consolidated
        
    except Exception as e:
        logger.error(f"Error en la consolidación de datos: {e}")
        return None


def run_etl_pipeline():
    """
    Ejecutar pipeline completo de ETL.
    """
    logger.info("=== INICIANDO PIPELINE ETL PREMIER LEAGUE ===")
    
    consolidated_df = consolidate_premier_league_data()
    
    if consolidated_df is not None:
        logger.info("=== PIPELINE ETL COMPLETADO EXITOSAMENTE ===")
        return consolidated_df
    else:
        logger.error("=== PIPELINE ETL FALLÓ ===")
        return None


if __name__ == "__main__":
    run_etl_pipeline()

