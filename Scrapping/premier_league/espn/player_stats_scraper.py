#!/usr/bin/env python3
"""
Scraper de estadísticas de jugadores de la Premier League desde ESPN.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from datetime import datetime
from loguru import logger
import sys
from playwright.sync_api import sync_playwright

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

# Categorías de estadísticas
STAT_CATEGORIES = {
    "goals": {
        "name": "Goals",
        "url_stat": "scoring",
        "main_column": "G",
        "description": "Goles"
    },
    "assists": {
        "name": "Assists",
        "url_stat": "assists",
        "main_column": "A",
        "description": "Asistencias"
    },
    "shots": {
        "name": "Shots",
        "url_stat": "shots",
        "main_column": "SH",
        "description": "Tiros"
    },
    "passes": {
        "name": "Passes",
        "url_stat": "passing",
        "main_column": "P",
        "description": "Pases"
    }
}


def scrape_player_stats(category="goals", season="2024", limit=50):
    """
    Extraer estadísticas de jugadores por categoría.
    
    Args:
        category (str): Categoría de estadísticas (goals, assists, shots, passes)
        season (str): Temporada (ej: "2024")
        limit (int): Número máximo de jugadores a extraer
        
    Returns:
        list: Lista de diccionarios con estadísticas de jugadores
    """
    if category not in STAT_CATEGORIES:
        logger.error(f"Categoría '{category}' no válida. Categorías disponibles: {list(STAT_CATEGORIES.keys())}")
        return None
    
    stat_info = STAT_CATEGORIES[category]
    url = f"https://www.espn.com/soccer/stats/_/league/ENG.1/season/{season}/view/{stat_info['url_stat']}"
    
    logger.info(f"Scrapeando estadísticas de {stat_info['name']} - Temporada {season}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(4000)  # Espera a que cargue el JS
            
            html = page.content()
            browser.close()
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Extraer estadísticas
        player_stats = extract_player_stats_data(soup, category, season)
        
        if player_stats:
            logger.info(f"Estadísticas de {stat_info['name']} extraídas exitosamente: {len(player_stats)} jugadores")
            return player_stats[:limit]
        else:
            logger.warning(f"No se pudieron extraer estadísticas de {stat_info['name']}")
            return None
            
    except Exception as e:
        logger.error(f"Error al scrapear estadísticas de {stat_info['name']}: {e}")
        return None


def extract_player_stats_data(soup, category, season):
    """
    Extraer datos de estadísticas de jugadores desde el HTML.
    
    Args:
        soup: BeautifulSoup object del HTML
        category (str): Categoría de estadísticas
        season (str): Temporada
        
    Returns:
        list: Lista de diccionarios con estadísticas de jugadores
    """
    try:
        player_stats = []
        
        # Buscar tablas de estadísticas
        tables = soup.find_all("table", class_="Table")
        
        for table in tables:
            rows = table.find_all("tr")
            
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 5:
                    continue
                
                try:
                    # Extraer datos del jugador
                    player_name = cells[0].get_text(strip=True)
                    team_name = cells[1].get_text(strip=True)
                    
                    # Extraer estadísticas según la categoría
                    if category == "goals":
                        goals = cells[2].get_text(strip=True)
                        games_played = cells[3].get_text(strip=True) if len(cells) > 3 else "0"
                        minutes = cells[4].get_text(strip=True) if len(cells) > 4 else "0"
                        
                        try:
                            player_data = {
                                'season': season,
                                'category': category,
                                'player_name': player_name,
                                'team_name': team_name,
                                'goals': int(goals),
                                'games_played': int(games_played),
                                'minutes': int(minutes)
                            }
                            player_stats.append(player_data)
                        except ValueError:
                            continue
                    
                    elif category == "assists":
                        assists = cells[2].get_text(strip=True)
                        games_played = cells[3].get_text(strip=True) if len(cells) > 3 else "0"
                        
                        try:
                            player_data = {
                                'season': season,
                                'category': category,
                                'player_name': player_name,
                                'team_name': team_name,
                                'assists': int(assists),
                                'games_played': int(games_played)
                            }
                            player_stats.append(player_data)
                        except ValueError:
                            continue
                    
                    # Agregar más categorías según sea necesario
                    
                except Exception as e:
                    logger.warning(f"Error al procesar fila de jugador: {e}")
                    continue
        
        return player_stats
        
    except Exception as e:
        logger.error(f"Error al extraer estadísticas de jugadores: {e}")
        return []


def scrape_all_player_stats(season="2024", categories=None, limit=50):
    """
    Scrapear estadísticas de jugadores para todas las categorías.
    
    Args:
        season (str): Temporada (ej: "2024")
        categories (list): Lista de categorías. Si None, usa todas.
        limit (int): Número máximo de jugadores por categoría
        
    Returns:
        pd.DataFrame: DataFrame con todas las estadísticas
    """
    if categories is None:
        categories = list(STAT_CATEGORIES.keys())
    
    logger.info(f"Iniciando scraping de estadísticas de jugadores - Temporada {season}")
    logger.info(f"Categorías: {', '.join(categories)}")
    
    all_stats = []
    
    for category in categories:
        try:
            stats = scrape_player_stats(category=category, season=season, limit=limit)
            if stats:
                all_stats.extend(stats)
            time.sleep(2)  # Pausa entre categorías
        except Exception as e:
            logger.error(f"Error procesando categoría {category}: {e}")
            continue
    
    if not all_stats:
        logger.warning("No se encontraron estadísticas de jugadores")
        return None
    
    df = pd.DataFrame(all_stats)
    logger.info(f"Total de registros de jugadores scrapeados: {len(df)}")
    
    return df


def save_player_stats_to_csv(df, season, output_dir="data/raw/player_stats"):
    """
    Guardar estadísticas de jugadores en CSV.
    
    Args:
        df (pd.DataFrame): DataFrame con estadísticas
        season (str): Temporada
        output_dir (str): Directorio de salida
    """
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"premier_league_player_stats_{season}.csv"
    filepath = os.path.join(output_dir, filename)
    
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info(f"Archivo guardado: {filepath}")
    logger.info(f"Total de registros: {len(df)}")


def main():
    """Función principal con argumentos de línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scraper de estadísticas de jugadores de Premier League desde ESPN'
    )
    
    parser.add_argument(
        '--season',
        type=str,
        default='2024',
        help='Temporada a scrapear (ej: "2024", "2023")'
    )
    
    parser.add_argument(
        '--category',
        type=str,
        choices=list(STAT_CATEGORIES.keys()),
        help='Categoría específica a scrapear (opcional)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Número máximo de jugadores por categoría (default: 50)'
    )
    
    args = parser.parse_args()
    
    # Si se especifica una categoría, usar solo esa
    categories = [args.category] if args.category else None
    
    # Scrapear estadísticas
    df = scrape_all_player_stats(season=args.season, categories=categories, limit=args.limit)
    
    if df is not None:
        # Guardar CSV
        save_player_stats_to_csv(df, args.season)
        logger.info("Scraping de estadísticas de jugadores completado exitosamente")
    else:
        logger.error("No se pudieron obtener estadísticas de jugadores")


if __name__ == "__main__":
    main()

