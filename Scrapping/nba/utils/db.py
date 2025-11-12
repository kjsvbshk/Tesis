from sqlalchemy import create_engine, text
import pandas as pd
import yaml
import os
from loguru import logger
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # Intentar cargar desde el directorio actual
    load_dotenv()

# Cargar configuración desde config.yaml (fallback)
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
config = {}
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

# Construir DATABASE_URL desde variables individuales o usar la completa
database_url = os.getenv("DATABASE_URL")

# Si no hay DATABASE_URL completa, construir desde variables individuales
if not database_url:
    db_host = os.getenv("NEON_DB_HOST") or config.get("DB_HOST")
    db_port = os.getenv("NEON_DB_PORT") or config.get("DB_PORT", "5432")
    db_name = os.getenv("NEON_DB_NAME") or config.get("DB_NAME")
    db_user = os.getenv("NEON_DB_USER") or config.get("DB_USER")
    db_password = os.getenv("NEON_DB_PASSWORD") or config.get("DB_PASSWORD")
    sslmode = os.getenv("NEON_DB_SSLMODE") or config.get("DB_SSLMODE", "require")
    channel_binding = os.getenv("NEON_DB_CHANNEL_BINDING") or config.get("DB_CHANNEL_BINDING", "require")
    
    if all([db_host, db_port, db_name, db_user, db_password]):
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode={sslmode}&channel_binding={channel_binding}"
    else:
        # Intentar desde config.yaml
        database_url = config.get("DATABASE_URL")
        # Reemplazar ${VAR} con variables de entorno si es necesario
        if database_url and database_url.startswith("${") and database_url.endswith("}"):
            env_var = database_url[2:-1]
            database_url = os.getenv(env_var) or database_url

if not database_url:
    raise ValueError(
        "DATABASE_URL no está configurada. "
        "Configúrala usando:\n"
        "  - Variables de entorno: DATABASE_URL o NEON_DB_* variables\n"
        "  - Archivo .env (copiar desde .env.example)\n"
        "  - Archivo config.yaml"
    )

schema = os.getenv("DB_SCHEMA") or config.get("DB_SCHEMA", "espn")

# Crear engine de conexión
engine = create_engine(database_url)

def load_to_db(df, table_name):
    """
    Cargar DataFrame a tabla de base de datos.
    
    Args:
        df (pd.DataFrame): DataFrame a cargar
        table_name (str): Nombre de la tabla
    """
    try:
        # Crear esquema si no existe
        create_schema_if_not_exists()
        
        # Cargar datos
        df.to_sql(
            table_name, 
            engine, 
            schema=schema,
            if_exists="append", 
            index=False,
            method='multi'
        )
        
        logger.info(f"Datos cargados exitosamente en {schema}.{table_name}: {len(df)} registros")
        
    except Exception as e:
        logger.error(f"Error al cargar datos en {schema}.{table_name}: {e}")
        raise

def create_schema_if_not_exists():
    """
    Crear esquema si no existe.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            conn.commit()
        logger.info(f"Esquema {schema} verificado/creado")
    except Exception as e:
        logger.error(f"Error al crear esquema {schema}: {e}")

def load_games_data():
    """
    Cargar datos de juegos desde dataset consolidado.
    """
    try:
        # Leer dataset consolidado
        df_path = "data/processed/nba_full_dataset.csv"
        if not os.path.exists(df_path):
            logger.error(f"Dataset consolidado no encontrado en {df_path}")
            return False
        
        df = pd.read_csv(df_path)
        
        # Preparar datos para tabla games
        games_df = prepare_games_data(df)
        
        if games_df is not None and not games_df.empty:
            load_to_db(games_df, "games")
            return True
        else:
            logger.warning("No hay datos de juegos para cargar")
            return False
            
    except Exception as e:
        logger.error(f"Error al cargar datos de juegos: {e}")
        return False

def prepare_games_data(df):
    """
    Preparar datos de juegos para carga a base de datos.
    
    Args:
        df (pd.DataFrame): Dataset consolidado
        
    Returns:
        pd.DataFrame: Datos preparados para tabla games
    """
    try:
        # Seleccionar columnas relevantes para tabla games
        games_columns = [
            'game_id', 'fecha', 'home_team', 'away_team', 'home_score', 'away_score',
            'home_win', 'point_diff', 'net_rating_diff', 'reb_diff', 'ast_diff', 'tov_diff',
            'home_fg_pct', 'home_3p_pct', 'home_ft_pct', 'home_reb', 'home_ast', 'home_stl', 'home_blk', 'home_to', 'home_pf', 'home_pts',
            'away_fg_pct', 'away_3p_pct', 'away_ft_pct', 'away_reb', 'away_ast', 'away_stl', 'away_blk', 'away_to', 'away_pf', 'away_pts'
        ]
        
        # Filtrar columnas que existen en el DataFrame
        existing_columns = [col for col in games_columns if col in df.columns]
        games_df = df[existing_columns].copy()
        
        # Convertir fecha a datetime
        if 'fecha' in games_df.columns:
            games_df['fecha'] = pd.to_datetime(games_df['fecha'], errors='coerce')
        
        return games_df
        
    except Exception as e:
        logger.error(f"Error al preparar datos de juegos: {e}")
        return None

def load_team_stats_data():
    """
    Cargar datos de estadísticas de equipos.
    """
    try:
        team_stats_dir = "data/raw/team_stats"
        if not os.path.exists(team_stats_dir):
            logger.warning(f"Directorio {team_stats_dir} no existe")
            return False
        
        # Leer todos los archivos CSV de estadísticas de equipos
        team_stats_data = []
        for filename in os.listdir(team_stats_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(team_stats_dir, filename)
                df = pd.read_csv(file_path)
                df['team_abbrev'] = filename.replace('.csv', '')
                team_stats_data.append(df)
        
        if team_stats_data:
            combined_df = pd.concat(team_stats_data, ignore_index=True)
            load_to_db(combined_df, "team_stats")
            return True
        else:
            logger.warning("No hay datos de estadísticas de equipos para cargar")
            return False
            
    except Exception as e:
        logger.error(f"Error al cargar datos de estadísticas de equipos: {e}")
        return False

def load_standings_data():
    """
    Cargar datos de clasificaciones.
    """
    try:
        standings_dir = "data/raw/standings"
        if not os.path.exists(standings_dir):
            logger.warning(f"Directorio {standings_dir} no existe")
            return False
        
        # Leer todos los archivos CSV de clasificaciones
        standings_data = []
        for filename in os.listdir(standings_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(standings_dir, filename)
                df = pd.read_csv(file_path)
                df['season'] = filename.replace('.csv', '')
                standings_data.append(df)
        
        if standings_data:
            combined_df = pd.concat(standings_data, ignore_index=True)
            load_to_db(combined_df, "standings")
            return True
        else:
            logger.warning("No hay datos de clasificaciones para cargar")
            return False
            
    except Exception as e:
        logger.error(f"Error al cargar datos de clasificaciones: {e}")
        return False

def load_injuries_data():
    """
    Cargar datos de lesiones.
    """
    try:
        injuries_dir = "data/raw/injuries"
        if not os.path.exists(injuries_dir):
            logger.warning(f"Directorio {injuries_dir} no existe")
            return False
        
        # Leer todos los archivos CSV de lesiones
        injuries_data = []
        for filename in os.listdir(injuries_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(injuries_dir, filename)
                df = pd.read_csv(file_path)
                df['report_date'] = filename.replace('.csv', '')
                injuries_data.append(df)
        
        if injuries_data:
            combined_df = pd.concat(injuries_data, ignore_index=True)
            load_to_db(combined_df, "injuries")
            return True
        else:
            logger.warning("No hay datos de lesiones para cargar")
            return False
            
    except Exception as e:
        logger.error(f"Error al cargar datos de lesiones: {e}")
        return False

def load_odds_data():
    """
    Cargar datos de cuotas.
    """
    try:
        odds_dir = "data/raw/odds"
        if not os.path.exists(odds_dir):
            logger.warning(f"Directorio {odds_dir} no existe")
            return False
        
        # Leer todos los archivos JSON de cuotas
        odds_data = []
        for filename in os.listdir(odds_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(odds_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    import json
                    data = json.load(f)
                    for game in data:
                        game['odds_date'] = filename.replace('.json', '')
                        odds_data.append(game)
        
        if odds_data:
            df = pd.DataFrame(odds_data)
            
            # Convertir columnas JSON a string para evitar errores de tipo
            if 'bookmakers' in df.columns:
                df['bookmakers'] = df['bookmakers'].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
            if 'markets' in df.columns:
                df['markets'] = df['markets'].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
            
            load_to_db(df, "odds")
            return True
        else:
            logger.warning("No hay datos de cuotas para cargar")
            return False
            
    except Exception as e:
        logger.error(f"Error al cargar datos de cuotas: {e}")
        return False

def load_all_data_to_db():
    """
    Cargar todos los datos a la base de datos.
    """
    logger.info("=== INICIANDO CARGA DE DATOS A BASE DE DATOS ===")
    
    results = {
        'games': load_games_data(),
        'team_stats': load_team_stats_data(),
        'standings': load_standings_data(),
        'injuries': load_injuries_data(),
        'odds': load_odds_data()
    }
    
    # Resumen de resultados
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    logger.info(f"=== CARGA COMPLETADA: {successful}/{total} tablas cargadas exitosamente ===")
    
    for table, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"{status} {table}")
    
    return results

def test_connection():
    """
    Probar conexión a la base de datos.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✓ Conexión a base de datos exitosa")
            return True
    except Exception as e:
        logger.error(f"✗ Error de conexión a base de datos: {e}")
        return False
