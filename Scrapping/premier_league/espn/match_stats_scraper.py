#!/usr/bin/env python3
"""
Scraper de estadísticas detalladas de partidos de la Premier League desde ESPN.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from datetime import datetime
from pathlib import Path
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


def scrape_match_stats(match_id):
    """
    Extraer estadísticas detalladas de un partido.
    
    Args:
        match_id (str): ID del partido en ESPN
        
    Returns:
        dict: Diccionario con estadísticas del partido
    """
    url = f"https://www.espn.com/soccer/match/_/gameId/{match_id}"
    logger.info(f"Scrapeando estadísticas del partido {match_id}")
    
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
        match_stats = extract_match_stats_data(soup, match_id)
        
        if match_stats:
            logger.info(f"Estadísticas extraídas exitosamente para partido {match_id}")
            return match_stats
        else:
            logger.warning(f"No se pudieron extraer estadísticas para partido {match_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error al scrapear estadísticas del partido {match_id}: {e}")
        return None


def extract_match_stats_data(soup, match_id):
    """
    Extraer datos de estadísticas del partido desde el HTML.
    
    Args:
        soup: BeautifulSoup object del HTML
        match_id (str): ID del partido
        
    Returns:
        dict: Diccionario con estadísticas del partido
    """
    try:
        stats = {
            'match_id': match_id,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Buscar información del partido
        # Extraer equipos
        team_elements = soup.find_all("div", class_="Team")
        if len(team_elements) >= 2:
            stats['home_team'] = team_elements[0].get_text(strip=True)
            stats['away_team'] = team_elements[1].get_text(strip=True)
        
        # Buscar tablas de estadísticas
        tables = soup.find_all("table", class_="Table")
        
        for table in tables:
            rows = table.find_all("tr")
            
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                
                # Extraer nombre de la estadística y valores
                stat_name = cells[0].get_text(strip=True).lower().replace(' ', '_')
                home_value = cells[1].get_text(strip=True)
                away_value = cells[2].get_text(strip=True)
                
                # Convertir valores numéricos
                try:
                    if '%' in home_value:
                        stats[f'home_{stat_name}'] = float(home_value.replace('%', ''))
                        stats[f'away_{stat_name}'] = float(away_value.replace('%', ''))
                    elif '.' in home_value:
                        stats[f'home_{stat_name}'] = float(home_value)
                        stats[f'away_{stat_name}'] = float(away_value)
                    else:
                        stats[f'home_{stat_name}'] = int(home_value)
                        stats[f'away_{stat_name}'] = int(away_value)
                except ValueError:
                    stats[f'home_{stat_name}'] = home_value
                    stats[f'away_{stat_name}'] = away_value
        
        # Valores por defecto si no se encuentran
        default_stats = {
            'home_possession': 0.0,
            'away_possession': 0.0,
            'home_shots': 0,
            'away_shots': 0,
            'home_shots_on_target': 0,
            'away_shots_on_target': 0,
            'home_passes': 0,
            'away_passes': 0,
            'home_pass_accuracy': 0.0,
            'away_pass_accuracy': 0.0,
            'home_fouls': 0,
            'away_fouls': 0,
            'home_yellow_cards': 0,
            'away_yellow_cards': 0,
            'home_red_cards': 0,
            'away_red_cards': 0,
            'home_corners': 0,
            'away_corners': 0,
            'home_offsides': 0,
            'away_offsides': 0
        }
        
        for key, value in default_stats.items():
            if key not in stats:
                stats[key] = value
        
        return stats
        
    except Exception as e:
        logger.error(f"Error al extraer estadísticas del partido {match_id}: {e}")
        return None


def scrape_matches_from_season(season="2024"):
    """
    Scrapear estadísticas de partidos de una temporada.
    Nota: Requiere obtener los match_ids primero desde matches_scraper.
    
    Args:
        season (str): Temporada (ej: "2024")
        
    Returns:
        pd.DataFrame: DataFrame con todas las estadísticas de partidos
    """
    logger.info(f"Iniciando scraping de estadísticas de partidos - Temporada {season}")
    
    # Leer match_ids desde los archivos raw de matches
    match_ids = []
    matches_dir = Path("data/raw")
    
    # Buscar archivos CSV de matches
    csv_files = list(matches_dir.glob("premier_league*.csv"))
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if 'match_id' in df.columns:
                # Filtrar match_ids válidos (que sean números, no strings complejos)
                valid_ids = df['match_id'].dropna()
                for match_id in valid_ids:
                    if isinstance(match_id, str) and match_id.isdigit():
                        match_ids.append(match_id)
                    elif isinstance(match_id, (int, float)) and not pd.isna(match_id):
                        match_ids.append(str(int(match_id)))
        except Exception as e:
            logger.warning(f"Error al leer {csv_file.name}: {e}")
            continue
    
    # Eliminar duplicados
    match_ids = list(set(match_ids))
    
    if not match_ids:
        logger.warning("No se encontraron match_ids válidos. Ejecuta primero matches_scraper para obtener los IDs.")
        return None
    
    logger.info(f"Encontrados {len(match_ids)} partidos únicos para scrapear")
    
    all_stats = []
    
    for match_id in match_ids:
        try:
            stats = scrape_match_stats(match_id)
            if stats:
                all_stats.append(stats)
            time.sleep(2)  # Pausa entre partidos
        except Exception as e:
            logger.error(f"Error procesando partido {match_id}: {e}")
            continue
    
    if not all_stats:
        logger.warning("No se encontraron estadísticas de partidos")
        return None
    
    df = pd.DataFrame(all_stats)
    logger.info(f"Total de partidos scrapeados: {len(df)}")
    
    return df


def save_match_stats_to_csv(df, season, output_dir="data/raw/match_stats"):
    """
    Guardar estadísticas de partidos en CSV.
    
    Args:
        df (pd.DataFrame): DataFrame con estadísticas
        season (str): Temporada
        output_dir (str): Directorio de salida
    """
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"premier_league_match_stats_{season}.csv"
    filepath = os.path.join(output_dir, filename)
    
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info(f"Archivo guardado: {filepath}")
    logger.info(f"Total de registros: {len(df)}")


def main():
    """Función principal con argumentos de línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scraper de estadísticas detalladas de partidos de Premier League desde ESPN'
    )
    
    parser.add_argument(
        '--season',
        type=str,
        default='2024',
        help='Temporada a scrapear (ej: "2024", "2023")'
    )
    
    parser.add_argument(
        '--match-id',
        type=str,
        help='Scrapear solo un partido específico por ID (opcional)'
    )
    
    args = parser.parse_args()
    
    # Si se especifica un match_id, usar solo ese
    if args.match_id:
        stats = scrape_match_stats(args.match_id)
        if stats:
            df = pd.DataFrame([stats])
            save_match_stats_to_csv(df, args.season)
            logger.info("Scraping de estadísticas del partido completado exitosamente")
        else:
            logger.error("No se pudieron obtener estadísticas del partido")
    else:
        # Scrapear estadísticas de todos los partidos de la temporada
        df = scrape_matches_from_season(season=args.season)
        
        if df is not None:
            # Guardar CSV
            save_match_stats_to_csv(df, args.season)
            logger.info("Scraping de estadísticas de partidos completado exitosamente")
        else:
            logger.error("No se pudieron obtener estadísticas de partidos")


if __name__ == "__main__":
    main()

