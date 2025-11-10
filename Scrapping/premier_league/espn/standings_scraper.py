#!/usr/bin/env python3
"""
Scraper de clasificaciones de la Premier League desde ESPN.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime
from loguru import logger
import sys

# Agregar utils al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

# Configurar logger
setup_logger()

HEADERS = {
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


def scrape_standings(season=None):
    """
    Extraer clasificaciones de la Premier League.
    
    Args:
        season (str): Temporada (ej: '2024'). Si None, usa temporada actual.
        
    Returns:
        list: Lista de diccionarios con datos de clasificaciones
    """
    url = "https://www.espn.com/soccer/standings/_/league/ENG.1"
    
    try:
        logger.info(f"Scrapeando clasificaciones de Premier League desde: {url}")
        
        res = requests.get(url, headers=HEADERS, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")
        
        # Extraer datos de clasificaciones
        standings_data = extract_standings_data(soup, season)
        
        if standings_data:
            logger.info(f"Clasificaciones extraídas exitosamente: {len(standings_data)} equipos")
            return standings_data
        else:
            logger.warning("No se pudieron extraer datos de clasificaciones")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error de conexión al obtener clasificaciones: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al procesar clasificaciones: {e}")
        return None


def extract_standings_data(soup, season=None):
    """
    Extraer datos de clasificaciones desde el HTML.
    
    Args:
        soup: BeautifulSoup object del HTML
        season (str): Temporada
        
    Returns:
        list: Lista de diccionarios con datos de equipos
    """
    try:
        standings = []
        
        if not season:
            current_year = datetime.now().year
            season = str(current_year)
        
        # Buscar tablas de clasificaciones
        tables = soup.find_all("table", class_="Table")
        logger.info(f"Encontradas {len(tables)} tablas de standings")
        
        for table in tables:
            rows = table.find_all("tr")
            
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 8:
                    continue
                
                try:
                    # Extraer datos de la fila
                    position = cells[0].get_text(strip=True)
                    team_name = cells[1].get_text(strip=True)
                    games_played = cells[2].get_text(strip=True)
                    wins = cells[3].get_text(strip=True)
                    draws = cells[4].get_text(strip=True)
                    losses = cells[5].get_text(strip=True)
                    goals_for = cells[6].get_text(strip=True)
                    goals_against = cells[7].get_text(strip=True)
                    goal_diff = cells[8].get_text(strip=True) if len(cells) > 8 else "0"
                    points = cells[9].get_text(strip=True) if len(cells) > 9 else "0"
                    
                    # Convertir a enteros
                    try:
                        position = int(position)
                        games_played = int(games_played)
                        wins = int(wins)
                        draws = int(draws)
                        losses = int(losses)
                        goals_for = int(goals_for)
                        goals_against = int(goals_against)
                        goal_diff = int(goal_diff)
                        points = int(points)
                    except ValueError:
                        continue
                    
                    team_data = {
                        'season': season,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'position': position,
                        'team_name': team_name,
                        'games_played': games_played,
                        'wins': wins,
                        'draws': draws,
                        'losses': losses,
                        'goals_for': goals_for,
                        'goals_against': goals_against,
                        'goal_diff': goal_diff,
                        'points': points
                    }
                    standings.append(team_data)
                    
                except Exception as e:
                    logger.warning(f"Error al procesar fila de standings: {e}")
                    continue
        
        logger.info(f"Total de equipos procesados: {len(standings)}")
        return standings
        
    except Exception as e:
        logger.error(f"Error al extraer datos de clasificaciones: {e}")
        return []


def save_standings_to_csv(standings_data, season=None):
    """
    Guardar clasificaciones en data/raw/standings/{season}.csv.
    
    Args:
        standings_data (list): Datos de clasificaciones
        season (str): Temporada
    """
    try:
        # Crear directorio si no existe
        os.makedirs("data/raw/standings", exist_ok=True)
        
        # Determinar nombre de archivo
        if not season:
            current_year = datetime.now().year
            season = str(current_year)
        
        # Crear DataFrame
        df = pd.DataFrame(standings_data)
        
        # Guardar CSV
        csv_path = f"data/raw/standings/{season}.csv"
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Clasificaciones guardadas en {csv_path}")
        logger.info(f"Total de equipos: {len(df)}")
        
    except Exception as e:
        logger.error(f"Error al guardar clasificaciones: {e}")


def main():
    """Función principal con argumentos de línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scraper de clasificaciones de Premier League desde ESPN'
    )
    
    parser.add_argument(
        '--season',
        type=str,
        default=None,
        help='Temporada a scrapear (ej: "2024"). Si no se especifica, usa temporada actual'
    )
    
    args = parser.parse_args()
    
    # Scrapear clasificaciones
    standings_data = scrape_standings(season=args.season)
    
    if standings_data:
        # Guardar CSV
        save_standings_to_csv(standings_data, season=args.season)
        logger.info("Scraping de clasificaciones completado exitosamente")
    else:
        logger.error("No se pudieron obtener las clasificaciones")


if __name__ == "__main__":
    main()

