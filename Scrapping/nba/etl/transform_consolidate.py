import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from loguru import logger

def consolidate_nba_data():
    """
    Unir los datasets obtenidos en un solo DataFrame maestro.
    
    Returns:
        pd.DataFrame: Dataset consolidado
    """
    logger.info("Iniciando consolidación de datos NBA")
    
    try:
        # Leer datasets individuales
        boxscores_df = read_boxscores_data()
        team_stats_df = read_team_stats_data()
        standings_df = read_standings_data()
        
        if boxscores_df is None or team_stats_df is None or standings_df is None:
            logger.error("No se pudieron cargar todos los datasets necesarios")
            return None
        
        # Combinar datasets
        consolidated_df = combine_datasets(boxscores_df, team_stats_df, standings_df)
        
        if consolidated_df is not None:
            # Calcular variables derivadas
            consolidated_df = calculate_derived_variables(consolidated_df)
            
            # Limpiar datos
            consolidated_df = clean_dataset(consolidated_df)
            
            # Guardar dataset final
            save_consolidated_dataset(consolidated_df)
            
            logger.info("Consolidación de datos completada exitosamente")
            return consolidated_df
        else:
            logger.error("Error en la consolidación de datasets")
            return None
            
    except Exception as e:
        logger.error(f"Error en la consolidación de datos: {e}")
        return None

def read_boxscores_data():
    """
    Leer datos de boxscores desde archivos JSON.
    
    Returns:
        pd.DataFrame: DataFrame con datos de boxscores
    """
    try:
        boxscores_dir = "data/raw/boxscores"
        boxscores_data = []
        
        if not os.path.exists(boxscores_dir):
            logger.warning(f"Directorio {boxscores_dir} no existe")
            return None
        
        # Leer todos los archivos JSON de boxscores
        for filename in os.listdir(boxscores_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(boxscores_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        game_data = json.load(f)
                    
                    # Procesar datos del juego
                    processed_game = process_boxscore_game(game_data)
                    if processed_game:
                        boxscores_data.append(processed_game)
                        
                except Exception as e:
                    logger.warning(f"Error al procesar {filename}: {e}")
                    continue
        
        if boxscores_data:
            df = pd.DataFrame(boxscores_data)
            logger.info(f"Boxscores cargados: {len(df)} juegos")
            return df
        else:
            logger.warning("No se encontraron datos de boxscores")
            return None
            
    except Exception as e:
        logger.error(f"Error al leer boxscores: {e}")
        return None

def process_boxscore_game(game_data):
    """
    Procesar datos de un juego individual de boxscore.
    
    Args:
        game_data (dict): Datos del juego
        
    Returns:
        dict: Datos procesados del juego
    """
    try:
        processed_game = {
            'game_id': game_data.get('game_id'),
            'fecha': game_data.get('fecha'),
            'home_team': game_data.get('home_team'),
            'away_team': game_data.get('away_team'),
            'home_score': game_data.get('home_score'),
            'away_score': game_data.get('away_score')
        }
        
        # Procesar estadísticas de equipos
        home_stats = game_data.get('home_stats', {})
        away_stats = game_data.get('away_stats', {})
        
        # Estadísticas del equipo local
        processed_game.update({
            'home_fg_pct': home_stats.get('FG%'),
            'home_3p_pct': home_stats.get('3P%'),
            'home_ft_pct': home_stats.get('FT%'),
            'home_reb': home_stats.get('REB'),
            'home_ast': home_stats.get('AST'),
            'home_stl': home_stats.get('STL'),
            'home_blk': home_stats.get('BLK'),
            'home_to': home_stats.get('TO'),
            'home_pf': home_stats.get('PF'),
            'home_pts': home_stats.get('PTS')
        })
        
        # Estadísticas del equipo visitante
        processed_game.update({
            'away_fg_pct': away_stats.get('FG%'),
            'away_3p_pct': away_stats.get('3P%'),
            'away_ft_pct': away_stats.get('FT%'),
            'away_reb': away_stats.get('REB'),
            'away_ast': away_stats.get('AST'),
            'away_stl': away_stats.get('STL'),
            'away_blk': away_stats.get('BLK'),
            'away_to': away_stats.get('TO'),
            'away_pf': away_stats.get('PF'),
            'away_pts': away_stats.get('PTS')
        })
        
        return processed_game
        
    except Exception as e:
        logger.error(f"Error al procesar juego de boxscore: {e}")
        return None

def read_team_stats_data():
    """
    Leer datos de estadísticas de equipos desde archivos CSV.
    Nueva estructura: data/raw/team_stats/{season}_{season_type}/offensive|defensive/all_teams.csv
    
    Returns:
        pd.DataFrame: DataFrame con estadísticas de equipos
    """
    try:
        team_stats_dir = "data/raw/team_stats"
        team_stats_data = []
        
        if not os.path.exists(team_stats_dir):
            logger.warning(f"Directorio {team_stats_dir} no existe")
            return None
        
        # Buscar archivos en la nueva estructura: {season}_{season_type}/offensive|defensive/all_teams.csv
        from pathlib import Path
        team_stats_path = Path(team_stats_dir)
        
        # Buscar en subdirectorios por temporada (formato: 2023-24_regular, 2024-25_playoffs, etc.)
        season_dirs = [d for d in team_stats_path.iterdir() if d.is_dir() and '_' in d.name]
        
        for season_dir in season_dirs:
            # Buscar en subdirectorios offensive y defensive
            for category_dir in ['offensive', 'defensive']:
                category_path = season_dir / category_dir
                if category_path.exists():
                    all_teams_file = category_path / 'all_teams.csv'
                    if all_teams_file.exists():
                        try:
                            df = pd.read_csv(all_teams_file)
                            # Extraer season y season_type del nombre del directorio
                            season_dir_name = season_dir.name
                            if '_' in season_dir_name:
                                parts = season_dir_name.split('_')
                                if len(parts) == 2:
                                    df['season'] = parts[0]
                                    df['season_type'] = parts[1]
                            df['category'] = category_dir
                            team_stats_data.append(df)
                        except Exception as e:
                            logger.warning(f"Error al procesar {all_teams_file}: {e}")
                            continue
        
        if team_stats_data:
            combined_df = pd.concat(team_stats_data, ignore_index=True)
            logger.info(f"Estadísticas de equipos cargadas: {len(combined_df)} registros")
            return combined_df
        else:
            logger.warning("No se encontraron datos de estadísticas de equipos")
            return None
            
    except Exception as e:
        logger.error(f"Error al leer estadísticas de equipos: {e}")
        return None

def read_standings_data():
    """
    Leer datos de clasificaciones desde archivos CSV.
    
    Returns:
        pd.DataFrame: DataFrame con clasificaciones
    """
    try:
        standings_dir = "data/raw/standings"
        standings_data = []
        
        if not os.path.exists(standings_dir):
            logger.warning(f"Directorio {standings_dir} no existe")
            return None
        
        # Leer todos los archivos CSV de clasificaciones
        for filename in os.listdir(standings_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(standings_dir, filename)
                
                try:
                    df = pd.read_csv(file_path)
                    df['season'] = filename.replace('.csv', '')
                    standings_data.append(df)
                    
                except Exception as e:
                    logger.warning(f"Error al procesar {filename}: {e}")
                    continue
        
        if standings_data:
            combined_df = pd.concat(standings_data, ignore_index=True)
            logger.info(f"Clasificaciones cargadas: {len(combined_df)} registros")
            return combined_df
        else:
            logger.warning("No se encontraron datos de clasificaciones")
            return None
            
    except Exception as e:
        logger.error(f"Error al leer clasificaciones: {e}")
        return None

def combine_datasets(boxscores_df, team_stats_df, standings_df):
    """
    Combinar datasets por team_name y season.
    
    Args:
        boxscores_df (pd.DataFrame): Datos de boxscores
        team_stats_df (pd.DataFrame): Estadísticas de equipos
        standings_df (pd.DataFrame): Clasificaciones
        
    Returns:
        pd.DataFrame: Dataset combinado
    """
    try:
        logger.info("Combinando datasets...")
        
        # Crear mapeo de nombres de equipos
        team_mapping = create_team_mapping()
        
        # Normalizar nombres de equipos en boxscores
        boxscores_df['home_team_normalized'] = boxscores_df['home_team'].map(team_mapping)
        boxscores_df['away_team_normalized'] = boxscores_df['away_team'].map(team_mapping)
        
        # Normalizar nombres de equipos en standings
        standings_df['team_normalized'] = standings_df['Team'].map(team_mapping)
        
        # Combinar boxscores con estadísticas de equipos
        # (Esta es una simplificación - en la práctica necesitarías lógica más compleja)
        combined_df = boxscores_df.copy()
        
        logger.info(f"Dataset combinado creado con {len(combined_df)} registros")
        return combined_df
        
    except Exception as e:
        logger.error(f"Error al combinar datasets: {e}")
        return None

def create_team_mapping():
    """
    Crear mapeo de nombres de equipos para normalización.
    Mapea nombres abreviados (como aparecen en los JSONs) a abreviaturas de 3 letras.
    
    Returns:
        dict: Mapeo de nombres de equipos a abreviaturas
    """
    return {
        # Nombres completos (por si acaso)
        'Boston Celtics': 'BOS',
        'Los Angeles Lakers': 'LAL',
        'Golden State Warriors': 'GSW',
        'Chicago Bulls': 'CHI',
        'Miami Heat': 'MIA',
        'San Antonio Spurs': 'SAS',
        'New York Knicks': 'NYK',
        'Brooklyn Nets': 'BKN',
        'Philadelphia 76ers': 'PHI',
        'Toronto Raptors': 'TOR',
        'Milwaukee Bucks': 'MIL',
        'Indiana Pacers': 'IND',
        'Cleveland Cavaliers': 'CLE',
        'Detroit Pistons': 'DET',
        'Atlanta Hawks': 'ATL',
        'Charlotte Hornets': 'CHA',
        'Orlando Magic': 'ORL',
        'Washington Wizards': 'WAS',
        'Dallas Mavericks': 'DAL',
        'Houston Rockets': 'HOU',
        'Memphis Grizzlies': 'MEM',
        'New Orleans Pelicans': 'NOP',
        'Phoenix Suns': 'PHX',
        'Sacramento Kings': 'SAC',
        'Oklahoma City Thunder': 'OKC',
        'Minnesota Timberwolves': 'MIN',
        'Los Angeles Clippers': 'LAC',
        'Denver Nuggets': 'DEN',
        'Portland Trail Blazers': 'POR',
        'Utah Jazz': 'UTA',
        # Nombres abreviados (como aparecen en los JSONs)
        'Celtics': 'BOS',
        'Lakers': 'LAL',
        'Warriors': 'GSW',
        'Bulls': 'CHI',
        'Heat': 'MIA',
        'Spurs': 'SAS',
        'Knicks': 'NYK',
        'Nets': 'BKN',
        '76ers': 'PHI',
        'Raptors': 'TOR',
        'Bucks': 'MIL',
        'Pacers': 'IND',
        'Cavaliers': 'CLE',
        'Pistons': 'DET',
        'Hawks': 'ATL',
        'Hornets': 'CHA',
        'Magic': 'ORL',
        'Wizards': 'WAS',
        'Mavericks': 'DAL',
        'Rockets': 'HOU',
        'Grizzlies': 'MEM',
        'Pelicans': 'NOP',
        'Suns': 'PHX',
        'Kings': 'SAC',
        'Thunder': 'OKC',
        'Timberwolves': 'MIN',
        'Clippers': 'LAC',
        'Nuggets': 'DEN',
        'Trail Blazers': 'POR',
        'Blazers': 'POR',
        'Jazz': 'UTA'
    }

def calculate_derived_variables(df):
    """
    Calcular variables derivadas.
    
    Args:
        df (pd.DataFrame): Dataset base
        
    Returns:
        pd.DataFrame: Dataset con variables derivadas
    """
    try:
        logger.info("Calculando variables derivadas...")
        
        # home_win: 1 si gana el equipo local, 0 si no
        df['home_win'] = (df['home_score'] > df['away_score']).astype(int)
        
        # point_diff: diferencia de puntos (local - visitante)
        df['point_diff'] = df['home_score'] - df['away_score']
        
        # net_rating_diff: diferencia de rating neto
        df['net_rating_diff'] = (df['home_fg_pct'] - df['away_fg_pct']) + (df['home_3p_pct'] - df['away_3p_pct'])
        
        # reb_diff: diferencia de rebotes
        df['reb_diff'] = df['home_reb'] - df['away_reb']
        
        # ast_diff: diferencia de asistencias
        df['ast_diff'] = df['home_ast'] - df['away_ast']
        
        # tov_diff: diferencia de turnovers (menos turnovers es mejor)
        df['tov_diff'] = df['away_to'] - df['home_to']  # Positivo si el local tiene menos turnovers
        
        logger.info("Variables derivadas calculadas exitosamente")
        return df
        
    except Exception as e:
        logger.error(f"Error al calcular variables derivadas: {e}")
        return df

def clean_dataset(df):
    """
    Eliminar duplicados y normalizar tipos.
    
    Args:
        df (pd.DataFrame): Dataset a limpiar
        
    Returns:
        pd.DataFrame: Dataset limpio
    """
    try:
        logger.info("Limpiando dataset...")
        
        initial_rows = len(df)
        
        # Eliminar duplicados
        df = df.drop_duplicates(subset=['game_id'], keep='first')
        
        # Normalizar tipos de datos
        numeric_columns = ['home_score', 'away_score', 'home_fg_pct', 'home_3p_pct', 
                          'home_ft_pct', 'home_reb', 'home_ast', 'home_stl', 'home_blk', 
                          'home_to', 'home_pf', 'home_pts', 'away_fg_pct', 'away_3p_pct', 
                          'away_ft_pct', 'away_reb', 'away_ast', 'away_stl', 'away_blk', 
                          'away_to', 'away_pf', 'away_pts', 'home_win', 'point_diff',
                          'net_rating_diff', 'reb_diff', 'ast_diff', 'tov_diff']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Eliminar filas con valores críticos faltantes
        critical_columns = ['game_id', 'home_team', 'away_team', 'home_score', 'away_score']
        df = df.dropna(subset=critical_columns)
        
        # Rellenar valores faltantes en estadísticas con 0
        stats_columns = [col for col in df.columns if col.endswith(('_pct', '_reb', '_ast', '_stl', '_blk', '_to', '_pf', '_pts'))]
        df[stats_columns] = df[stats_columns].fillna(0)
        
        final_rows = len(df)
        removed_rows = initial_rows - final_rows
        
        logger.info(f"Dataset limpio: {removed_rows} filas eliminadas, {final_rows} filas restantes")
        return df
        
    except Exception as e:
        logger.error(f"Error al limpiar dataset: {e}")
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
        output_path = "data/processed/nba_full_dataset.csv"
        df.to_csv(output_path, index=False)
        
        logger.info(f"Dataset consolidado guardado en {output_path}")
        logger.info(f"Dimensiones del dataset: {df.shape}")
        logger.info(f"Columnas: {list(df.columns)}")
        
    except Exception as e:
        logger.error(f"Error al guardar dataset consolidado: {e}")

def run_etl_pipeline():
    """
    Ejecutar pipeline completo de ETL.
    """
    logger.info("=== INICIANDO PIPELINE ETL NBA ===")
    
    consolidated_df = consolidate_nba_data()
    
    if consolidated_df is not None:
        logger.info("=== PIPELINE ETL COMPLETADO EXITOSAMENTE ===")
        return consolidated_df
    else:
        logger.error("=== PIPELINE ETL FALLÓ ===")
        return None
