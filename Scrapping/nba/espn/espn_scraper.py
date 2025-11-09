import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from loguru import logger

def scrape_boxscore(game_id):
    """
    Extraer datos de rendimiento por equipo de cada partido.
    
    Args:
        game_id (str): ID único del juego
        
    Returns:
        dict: Datos del boxscore con game_id, fecha, equipos, scores y estadísticas
    """
    url = f"https://www.espn.com/nba/boxscore/_/gameId/{game_id}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")
        
        # Parse equipos
        teams = [t.text for t in soup.select(".ScoreCell__TeamName")]
        scores = [s.text for s in soup.select(".ScoreCell__Score")]
        
        # Parse tabla de estadísticas
        team_stats = soup.select("table.mod-data")
        
        # Extraer datos básicos del juego
        game_data = {
            "game_id": game_id,
            "fecha": extract_game_date(soup),
            "home_team": teams[1] if len(teams) > 1 else None,
            "away_team": teams[0] if len(teams) > 0 else None,
            "home_score": int(scores[1]) if len(scores) > 1 and scores[1].isdigit() else None,
            "away_score": int(scores[0]) if len(scores) > 0 and scores[0].isdigit() else None
        }
        
        # Extraer estadísticas de equipos
        if team_stats:
            home_stats = extract_team_stats(team_stats[1]) if len(team_stats) > 1 else {}
            away_stats = extract_team_stats(team_stats[0]) if len(team_stats) > 0 else {}
            
            game_data["home_stats"] = home_stats
            game_data["away_stats"] = away_stats
        
        logger.info(f"Boxscore extraído exitosamente para game_id: {game_id}")
        return game_data
        
    except requests.RequestException as e:
        logger.error(f"Error de conexión al obtener boxscore {game_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al procesar boxscore {game_id}: {e}")
        return None

def extract_game_date(soup):
    """
    Extraer fecha del juego desde el HTML.
    
    Args:
        soup: BeautifulSoup object del HTML
        
    Returns:
        str: Fecha en formato YYYY-MM-DD
    """
    try:
        # Buscar fecha en el HTML (puede variar según estructura de ESPN)
        date_element = soup.find("span", class_="date")
        if date_element:
            return date_element.text.strip()
        
        # Fallback: usar fecha actual si no se encuentra
        return datetime.now().strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def extract_team_stats(team_table):
    """
    Extraer estadísticas de equipo desde la tabla.
    
    Args:
        team_table: BeautifulSoup table element
        
    Returns:
        dict: Estadísticas del equipo
    """
    stats = {}
    
    try:
        # Buscar fila "TOTALS" en la tabla
        totals_row = team_table.find("tr", class_="Table__TR--sm")
        if not totals_row:
            # Buscar alternativa
            totals_row = team_table.find("tr", string=lambda text: text and "TOTALS" in text.upper())
        
        if totals_row:
            cells = totals_row.find_all("td")
            if len(cells) >= 10:  # Asegurar que tenemos suficientes columnas
                stats = {
                    "FG%": parse_stat(cells[1].text) if len(cells) > 1 else None,
                    "3P%": parse_stat(cells[3].text) if len(cells) > 3 else None,
                    "FT%": parse_stat(cells[5].text) if len(cells) > 5 else None,
                    "REB": parse_stat(cells[6].text) if len(cells) > 6 else None,
                    "AST": parse_stat(cells[7].text) if len(cells) > 7 else None,
                    "STL": parse_stat(cells[8].text) if len(cells) > 8 else None,
                    "BLK": parse_stat(cells[9].text) if len(cells) > 9 else None,
                    "TO": parse_stat(cells[10].text) if len(cells) > 10 else None,
                    "PF": parse_stat(cells[11].text) if len(cells) > 11 else None,
                    "PTS": parse_stat(cells[12].text) if len(cells) > 12 else None
                }
        
        logger.debug(f"Estadísticas extraídas: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error al extraer estadísticas de equipo: {e}")
        return {}

def parse_stat(stat_text):
    """
    Parsear valor estadístico desde texto.
    
    Args:
        stat_text (str): Texto de la estadística
        
    Returns:
        float or int: Valor parseado o None si no se puede parsear
    """
    try:
        # Limpiar texto
        clean_text = stat_text.strip().replace("%", "")
        
        # Si es porcentaje, convertir a float
        if "%" in stat_text:
            return float(clean_text) if clean_text else None
        
        # Si es número entero, convertir a int
        if clean_text.isdigit():
            return int(clean_text)
        
        # Si es decimal, convertir a float
        if "." in clean_text:
            return float(clean_text)
        
        return None
    except:
        return None

def save_boxscore_to_json(game_data, game_id):
    """
    Guardar boxscore en data/raw/boxscores/{game_id}.json.
    
    Args:
        game_data (dict): Datos del boxscore
        game_id (str): ID del juego
    """
    try:
        # Crear directorio si no existe
        os.makedirs("data/raw/boxscores", exist_ok=True)
        
        # Guardar JSON
        json_path = f"data/raw/boxscores/{game_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Boxscore guardado en {json_path}")
        
    except Exception as e:
        logger.error(f"Error al guardar boxscore {game_id}: {e}")

def run_scraper(limit=100):
    """
    Función principal que orquesta todo el proceso de scraping.
    
    Args:
        limit (int): Límite de juegos a procesar (opcional)
        
    Returns:
        bool: True si el scraping fue exitoso, False si falló
    """
    from espn.espn_schedule_scraper import scrape_season_game_ids
    from espn.team_scraper import scrape_all_teams_stats
    from espn.standings_scraper import scrape_current_standings
    from espn.injuries_scraper import scrape_current_injuries
    from espn.odds_scraper import scrape_current_odds
    from etl.transform_consolidate import run_etl_pipeline
    from utils.db import load_all_data_to_db, test_connection
    from datetime import datetime, timedelta
    
    logger.info("=== INICIANDO PROCESO COMPLETO DE SCRAPING NBA ===")
    start_time = datetime.now()
    
    try:
        # 1. Probar conexión a base de datos
        if not test_connection():
            logger.error("No se puede conectar a la base de datos")
            return False
        
        # 2. Obtener game IDs (últimos 7 días)
        logger.info("Paso 1/7: Obteniendo game IDs...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        scrape_season_game_ids(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d")
        )
        
        # 3. Scrapear boxscores
        logger.info("Paso 2/7: Scrapeando boxscores...")
        # Aquí se implementaría la lógica para scrapear boxscores usando los game IDs
        
        # 4. Scrapear estadísticas de equipos
        logger.info("Paso 3/7: Scrapeando estadísticas de equipos...")
        scrape_all_teams_stats()
        
        # 5. Scrapear clasificaciones
        logger.info("Paso 4/7: Scrapeando clasificaciones...")
        scrape_current_standings()
        
        # 6. Scrapear lesiones
        logger.info("Paso 5/7: Scrapeando reportes de lesiones...")
        scrape_current_injuries()
        
        # 7. Scrapear cuotas (opcional)
        logger.info("Paso 6/7: Scrapeando cuotas...")
        scrape_current_odds()
        
        # 8. Ejecutar ETL
        logger.info("Paso 7/7: Ejecutando pipeline ETL...")
        etl_result = run_etl_pipeline()
        
        if etl_result is not None:
            # 9. Cargar a base de datos
            logger.info("Cargando datos a base de datos...")
            db_results = load_all_data_to_db()
            
            # Verificar resultados
            successful_tables = sum(1 for success in db_results.values() if success)
            total_tables = len(db_results)
            
            if successful_tables == total_tables:
                end_time = datetime.now()
                duration = end_time - start_time
                logger.info(f"=== SCRAPING COMPLETADO EXITOSAMENTE ===")
                logger.info(f"Duración total: {duration}")
                logger.info(f"Tablas cargadas: {successful_tables}/{total_tables}")
                return True
            else:
                logger.error(f"Error en carga de datos: {successful_tables}/{total_tables} tablas cargadas")
                return False
        else:
            logger.error("Error en pipeline ETL")
            return False
            
    except Exception as e:
        logger.error(f"Error crítico en proceso de scraping: {e}")
        return False

def validate_duplicates(game_id):
    """
    Validar si un game_id ya existe (evitar duplicados).
    
    Args:
        game_id (str): ID del juego a validar
        
    Returns:
        bool: True si es único, False si ya existe
    """
    try:
        import os
        json_path = f"data/raw/boxscores/{game_id}.json"
        return not os.path.exists(json_path)
    except Exception as e:
        logger.error(f"Error al validar duplicados para {game_id}: {e}")
        return True  # En caso de error, permitir procesamiento
