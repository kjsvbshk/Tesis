#!/usr/bin/env python3
"""
Scraper de resultados de la Premier League desde ESPN usando Playwright.
Refactorizado siguiendo la estructura de NBA.
"""

import time
import os
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from datetime import datetime
from loguru import logger
import sys

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


def fetch_team_results(team_id, team_name, season="2024"):
    """
    Obtiene los resultados de un equipo desde la versión dinámica de ESPN.
    
    Args:
        team_id (int): ID del equipo en ESPN
        team_name (str): Nombre del equipo
        season (str): Temporada (ej: "2024", "2023")
    
    Returns:
        list: Lista de diccionarios con los campos principales
    """
    url = f"https://www.espn.com/soccer/team/results/_/id/{team_id}/season/{season}"
    logger.info(f"Scrapeando resultados de {team_name} (temporada {season})")
    
    matches = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(4000)  # Espera a que cargue el JS
            
            html = page.content()
            browser.close()
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Recorrer las tablas de partidos
        for table in soup.select("table.Table"):
            for row in table.select("tbody tr"):
                cells = row.select("td")
                if len(cells) < 6:
                    continue
                
                # Extraer datos principales
                date = cells[0].get_text(strip=True)
                home_team = cells[1].get_text(strip=True)
                score = cells[2].get_text(strip=True)
                away_team = cells[3].get_text(strip=True)
                status = cells[4].get_text(strip=True)
                competition = cells[5].get_text(strip=True)
                
                # Filtrar solo Premier League
                if "Premier League" not in competition:
                    continue
                
                # Determinar local/visitante
                if team_name == home_team:
                    venue = "Home"
                    opponent = away_team
                    our_goals_index = 0
                elif team_name == away_team:
                    venue = "Away"
                    opponent = home_team
                    our_goals_index = 1
                else:
                    continue
                
                # Limpiar marcador
                score_clean = score.replace("–", "-").replace("—", "-").strip()
                if "-" not in score_clean:
                    continue
                
                try:
                    home_goals, away_goals = map(str.strip, score_clean.split("-", 1))
                    goals = [int(home_goals), int(away_goals)]
                except ValueError:
                    logger.warning(f"Error al parsear marcador: {score_clean}")
                    continue
                
                goals_for = goals[our_goals_index]
                goals_against = goals[1 - our_goals_index]
                
                # Resultado y diferencia de goles
                if goals_for > goals_against:
                    result = "W"
                elif goals_for < goals_against:
                    result = "L"
                else:
                    result = "D"
                
                goal_diff = goals_for - goals_against
                
                # Convertir fecha
                try:
                    # Intentar parsear fecha con año
                    parsed_date = datetime.strptime(date, "%a, %b %d").replace(year=int(season))
                    date_iso = parsed_date.strftime("%Y-%m-%d")
                except Exception:
                    # Si falla, usar la fecha tal cual
                    date_iso = date
                
                matches.append({
                    "season": season,
                    "team_name": team_name,
                    "team_id": team_id,
                    "date": date_iso,
                    "venue": venue,
                    "opponent": opponent,
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "goal_diff": goal_diff,
                    "result": result,
                    "status": status,
                    "competition": competition
                })
        
        logger.info(f"  → {len(matches)} partidos encontrados para {team_name}")
        return matches
        
    except Exception as e:
        logger.error(f"Error al scrapear {team_name}: {e}")
        return []


def scrape_season_matches(season="2024", teams=None):
    """
    Scrapear todos los partidos de una temporada.
    
    Args:
        season (str): Temporada (ej: "2024", "2023")
        teams (dict): Diccionario de equipos. Si None, usa todos los equipos de Premier League.
    
    Returns:
        pd.DataFrame: DataFrame con todos los partidos
    """
    if teams is None:
        teams = PREMIER_LEAGUE_TEAMS
    
    logger.info(f"Iniciando scraping de Premier League - Temporada {season}")
    logger.info(f"Total de equipos: {len(teams)}")
    
    all_matches = []
    
    for name, tid in teams.items():
        try:
            data = fetch_team_results(tid, name, season)
            all_matches.extend(data)
            time.sleep(1)  # Pausa entre equipos
        except Exception as e:
            logger.error(f"Error procesando {name}: {e}")
            continue
    
    if not all_matches:
        logger.warning("No se encontraron partidos")
        return None
    
    df = pd.DataFrame(all_matches)
    logger.info(f"Total de partidos scrapeados: {len(df)}")
    
    return df


def save_matches_to_csv(df, season, output_dir="data/raw"):
    """
    Guardar partidos en CSV.
    
    Args:
        df (pd.DataFrame): DataFrame con partidos
        season (str): Temporada
        output_dir (str): Directorio de salida
    """
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"premier_league_matches_{season}.csv"
    filepath = os.path.join(output_dir, filename)
    
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info(f"Archivo guardado: {filepath}")
    logger.info(f"Total de registros: {len(df)}")


def main():
    """Función principal con argumentos de línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scraper de resultados de Premier League desde ESPN'
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
    
    # Scrapear partidos
    df = scrape_season_matches(season=args.season, teams=teams)
    
    if df is not None:
        # Guardar CSV
        save_matches_to_csv(df, args.season)
        logger.info("Scraping completado exitosamente")
    else:
        logger.error("No se pudieron obtener partidos")


if __name__ == "__main__":
    main()

