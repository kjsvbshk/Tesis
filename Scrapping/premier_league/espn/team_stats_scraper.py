#!/usr/bin/env python3
"""
Scraper de estadísticas de equipos de la Premier League desde ESPN.
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

# Equipos de Premier League con sus IDs de ESPN
PREMIER_LEAGUE_TEAMS = {
    "Arsenal": 359,
    "Aston Villa": 362,
    "Brentford": 337,
    "Brighton & Hove Albion": 331,
    "Burnley": 328,
    "Chelsea": 363,
    "Crystal Palace": 384,
    "Everton": 368,
    "Leeds United": 341,
    "Leicester City": 375,
    "Liverpool": 364,
    "Manchester City": 382,
    "Manchester United": 360,
    "Newcastle United": 361,
    "Norwich City": 393,
    "Southampton": 376,
    "Tottenham Hotspur": 367,
    "Watford": 395,
    "West Ham United": 371,
    "Wolverhampton Wanderers": 380
}

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


def scrape_team_stats(team_id, team_name, season="2024"):
    """
    Extraer estadísticas de un equipo de la Premier League.
    
    Args:
        team_id (int): ID del equipo en ESPN
        team_name (str): Nombre del equipo
        season (str): Temporada (ej: "2024")
        
    Returns:
        dict: Diccionario con estadísticas del equipo
    """
    url = f"https://www.espn.com/soccer/team/stats/_/id/{team_id}/league/ENG.1/season/{season}"
    logger.info(f"Scrapeando estadísticas de {team_name} (temporada {season})")
    
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
        team_stats = extract_team_stats_data(soup, team_name, season)
        
        if team_stats:
            logger.info(f"Estadísticas extraídas exitosamente para {team_name}")
            return team_stats
        else:
            logger.warning(f"No se pudieron extraer estadísticas para {team_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error al scrapear estadísticas de {team_name}: {e}")
        return None


def extract_team_stats_data(soup, team_name, season):
    """
    Extraer datos de estadísticas desde el HTML.
    
    Args:
        soup: BeautifulSoup object del HTML
        team_name (str): Nombre del equipo
        season (str): Temporada
        
    Returns:
        dict: Diccionario con estadísticas del equipo
    """
    try:
        stats = {
            'season': season,
            'team_name': team_name,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Buscar tablas de estadísticas
        tables = soup.find_all("table", class_="Table")
        
        for table in tables:
            # Verificar si es una tabla de estadísticas (no de jugadores)
            table_text = table.get_text().lower()
            # Filtrar tablas que contienen nombres de jugadores o no son estadísticas
            if any(keyword in table_text for keyword in ['player', 'name', 'position', 'age', 'height', 'weight']):
                continue
            
            rows = table.find_all("tr")
            
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                
                # Extraer nombre de la estadística y valor
                stat_name = cells[0].get_text(strip=True).lower().replace(' ', '_')
                stat_value = cells[1].get_text(strip=True)
                
                # Filtrar nombres de jugadores o valores no numéricos
                if not stat_value or stat_value.isalpha():
                    continue
                
                # Convertir valores numéricos
                try:
                    # Limpiar valores (remover %, comas, etc.)
                    stat_value_clean = stat_value.replace('%', '').replace(',', '').strip()
                    if '.' in stat_value_clean:
                        stats[stat_name] = float(stat_value_clean)
                    else:
                        stats[stat_name] = int(stat_value_clean)
                except ValueError:
                    # Si no es numérico, saltar
                    continue
        
        # Valores por defecto si no se encuentran
        default_stats = {
            'goals_per_game': 0.0,
            'goals_against_per_game': 0.0,
            'possession_pct': 0.0,
            'shots_per_game': 0.0,
            'shots_on_target_per_game': 0.0,
            'passes_completed': 0,
            'pass_accuracy_pct': 0.0,
            'clean_sheets': 0,
            'yellow_cards': 0,
            'red_cards': 0,
            'fouls_per_game': 0.0
        }
        
        for key, value in default_stats.items():
            if key not in stats:
                stats[key] = value
        
        return stats
        
    except Exception as e:
        logger.error(f"Error al extraer estadísticas de {team_name}: {e}")
        return None


def scrape_all_teams_stats(season="2024", teams=None):
    """
    Scrapear estadísticas de todos los equipos.
    
    Args:
        season (str): Temporada (ej: "2024")
        teams (dict): Diccionario de equipos. Si None, usa todos los equipos de Premier League.
        
    Returns:
        pd.DataFrame: DataFrame con todas las estadísticas
    """
    if teams is None:
        teams = PREMIER_LEAGUE_TEAMS
    
    logger.info(f"Iniciando scraping de estadísticas de equipos - Temporada {season}")
    logger.info(f"Total de equipos: {len(teams)}")
    
    all_stats = []
    
    for name, tid in teams.items():
        try:
            stats = scrape_team_stats(tid, name, season)
            if stats:
                all_stats.append(stats)
            time.sleep(2)  # Pausa entre equipos
        except Exception as e:
            logger.error(f"Error procesando {name}: {e}")
            continue
    
    if not all_stats:
        logger.warning("No se encontraron estadísticas")
        return None
    
    df = pd.DataFrame(all_stats)
    logger.info(f"Total de equipos scrapeados: {len(df)}")
    
    return df


def save_team_stats_to_csv(df, season, output_dir="data/raw/team_stats"):
    """
    Guardar estadísticas de equipos en CSV.
    
    Args:
        df (pd.DataFrame): DataFrame con estadísticas
        season (str): Temporada
        output_dir (str): Directorio de salida
    """
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"premier_league_team_stats_{season}.csv"
    filepath = os.path.join(output_dir, filename)
    
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info(f"Archivo guardado: {filepath}")
    logger.info(f"Total de registros: {len(df)}")


def main():
    """Función principal con argumentos de línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scraper de estadísticas de equipos de Premier League desde ESPN'
    )
    
    parser.add_argument(
        '--season',
        type=str,
        default='2024',
        help='Temporada a scrapear (ej: "2024", "2023")'
    )
    
    parser.add_argument(
        '--team',
        type=str,
        help='Scrapear solo un equipo específico (opcional)'
    )
    
    args = parser.parse_args()
    
    # Si se especifica un equipo, usar solo ese
    teams = None
    if args.team:
        if args.team in PREMIER_LEAGUE_TEAMS:
            teams = {args.team: PREMIER_LEAGUE_TEAMS[args.team]}
            logger.info(f"Scrapeando solo: {args.team}")
        else:
            logger.error(f"Equipo '{args.team}' no encontrado")
            logger.info(f"Equipos disponibles: {', '.join(PREMIER_LEAGUE_TEAMS.keys())}")
            return
    
    # Scrapear estadísticas
    df = scrape_all_teams_stats(season=args.season, teams=teams)
    
    if df is not None:
        # Guardar CSV
        save_team_stats_to_csv(df, args.season)
        logger.info("Scraping de estadísticas de equipos completado exitosamente")
    else:
        logger.error("No se pudieron obtener estadísticas de equipos")


if __name__ == "__main__":
    main()

