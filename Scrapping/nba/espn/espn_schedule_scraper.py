import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import os

def get_game_ids_by_date(date: str):
    """
    Obtener los IDs únicos de todos los partidos de una fecha específica.
    
    Args:
        date (str): Fecha en formato YYYYMMDD
        
    Returns:
        list: Lista de game IDs encontrados
    """
    url = f"https://www.espn.com/nba/schedule/_/date/{date}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "lxml")
        # Buscar enlaces con patrón /nba/game/_/gameId/ o boxscore/_/gameId/
        ids = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/game/_/gameId/" in href or "boxscore/_/gameId/" in href:
                # Extraer game ID numérico del href
                # Ejemplo: /nba/game/_/gameId/401584773/warriors-pistons
                parts = href.split("/")
                for part in parts:
                    if part.isdigit() and len(part) > 6:  # Game IDs son números largos
                        ids.append(part)
                        break
        
        logger.info(f"Encontrados {len(ids)} game IDs para la fecha {date}")
        return ids
        
    except requests.RequestException as e:
        logger.error(f"Error al obtener datos para fecha {date}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado para fecha {date}: {e}")
        return []

def scrape_season_game_ids(season_start: str, season_end: str):
    """
    Ejecutar scraping para cada fecha entre season_start y season_end.
    
    Args:
        season_start (str): Fecha de inicio en formato YYYYMMDD
        season_end (str): Fecha de fin en formato YYYYMMDD
    """
    # Convertir strings a datetime
    start_date = datetime.strptime(season_start, "%Y%m%d")
    end_date = datetime.strptime(season_end, "%Y%m%d")
    
    all_game_ids = []
    current_date = start_date
    
    logger.info(f"Iniciando scraping de game IDs desde {season_start} hasta {season_end}")
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        game_ids = get_game_ids_by_date(date_str)
        
        # Agregar game IDs con fecha
        for game_id in game_ids:
            all_game_ids.append({
                'date': date_str,
                'game_id': game_id
            })
        
        current_date += timedelta(days=1)
    
    # Guardar en CSV
    save_game_ids_to_csv(all_game_ids)
    
    logger.info(f"Scraping completado. Total de game IDs encontrados: {len(all_game_ids)}")

def scrape_2023_24_season():
    """
    Scrapear temporada 2023-24 completa (octubre 2023 - abril 2024).
    """
    logger.info("=== SCRAPEANDO TEMPORADA 2023-24 COMPLETA ===")
    
    # Temporada 2023-24: Octubre 2023 a Abril 2024
    season_start = "20231024"  # Inicio de temporada 2023-24
    season_end = "20240414"    # Fin de temporada regular 2023-24
    
    scrape_season_game_ids(season_start, season_end)

def save_game_ids_to_csv(game_ids_data):
    """
    Guardar game IDs en data/raw/game_ids.csv.
    
    Args:
        game_ids_data (list): Lista de diccionarios con date y game_id
    """
    # Crear directorio si no existe
    os.makedirs("data/raw", exist_ok=True)
    
    # Crear DataFrame y guardar
    df = pd.DataFrame(game_ids_data)
    csv_path = "data/raw/game_ids.csv"
    df.to_csv(csv_path, index=False)
    
    logger.info(f"Game IDs guardados en {csv_path}")
    logger.info(f"Total de registros: {len(df)}")
