"""
Script completo para scrapear schedule de NBA.com y hacer match con ESPN

Proceso:
1. Scrapear schedule completo de NBA.com para 2024-25 y 2025-26
2. Cargar datos de ESPN (boxscores)
3. Hacer match por fecha + equipos
4. Guardar mapeo ESPN game_id → NBA.com game_id
"""

import json
import os
from datetime import datetime, timedelta
from loguru import logger
from tqdm import tqdm
import time
from pathlib import Path

from nba_com.schedule_scraper import scrape_season_schedule

# Rangos de fechas para cada temporada
SEASON_RANGES = {
    '2023-24': {
        'start': '2023-10-24',  # Inicio temporada 2023-24
        'end': '2024-06-20'     # Fin playoffs (aprox)
    },
    '2024-25': {
        'start': '2024-10-22',  # Inicio temporada regular 2024-25
        'end': '2025-06-30'     # Fin playoffs
    },
    '2025-26': {
        'start': '2025-10-21',  # Inicio temporada regular 2025-26
        'end': '2026-06-30'     # Fin playoffs
    }
}

def scrape_full_nba_schedule(output_file='data/nba_com_schedule.json', delay=0.3):
    """
    Scrapear schedule completo de NBA.com para ambas temporadas
    
    Args:
        output_file: Archivo de salida
        delay: Delay entre requests (segundos)
        
    Returns:
        list de todos los juegos
    """
    all_games = []
    
    for season, dates in SEASON_RANGES.items():
        logger.info(f"Scrapeando temporada {season}: {dates['start']} a {dates['end']}")
        
        games = scrape_season_schedule(
            start_date=dates['start'],
            end_date=dates['end'],
            delay=delay
        )
        
        # Agregar season info
        for game in games:
            game['season'] = season
        
        all_games.extend(games)
        logger.success(f"✅ Temporada {season}: {len(games)} juegos")
    
    # Guardar
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_games, f, indent=2, ensure_ascii=False)
    
    logger.success(f"💾 Schedule completo guardado: {output_file}")
    logger.info(f"Total juegos: {len(all_games)}")
    
    return all_games

def load_espn_games(boxscores_dir='data/raw/boxscores'):
    """
    Cargar juegos de ESPN desde boxscores
    
    Returns:
        dict: {espn_game_id: {fecha, home_team, away_team}}
    """
    espn_games = {}
    
    boxscore_files = list(Path(boxscores_dir).glob('*.json'))
    
    logger.info(f"Cargando {len(boxscore_files)} boxscores de ESPN...")
    
    for file_path in boxscore_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            espn_game_id = file_path.stem
            
            espn_games[espn_game_id] = {
                'fecha': data.get('fecha'),
                'home_team': data.get('home_team'),
                'away_team': data.get('away_team'),
                'home_score': int(data.get('home_score', 0) or 0),
                'away_score': int(data.get('away_score', 0) or 0)
            }
        except Exception as e:
            logger.warning(f"Error leyendo {file_path.name}: {e}")
            continue
    
    logger.success(f"✅ Cargados {len(espn_games)} juegos de ESPN")
    return espn_games

def match_games(nba_games, espn_games):
    """
    Hacer match entre juegos de NBA.com y ESPN por fecha + equipos
    
    Args:
        nba_games: Lista de juegos de NBA.com
        espn_games: Dict de juegos de ESPN
        
    Returns:
        dict: {espn_game_id: nba_game_id}
    """
    mapping = {}
    unmatched_espn = []
    unmatched_nba = []
    
    # Crear índice de NBA games por scores + equipos
    nba_index = {}
    for game in nba_games:
        # Score matching es más confiable ya que las fechas en ESPN están mal (son fecha de scraping)
        # Usamos: (away_tricode, home_tricode, away_score, home_score)
        key = (
            game['away_tricode'], 
            game['home_tricode'], 
            game.get('away_score', 0), 
            game.get('home_score', 0)
        )
        nba_index[key] = game['nba_game_id']
    
    # Mapeo de nombres completos de ESPN a tricodes de NBA.com
    TEAM_NAME_TO_TRICODE = {
        'Atlanta Hawks': 'ATL',
        'Boston Celtics': 'BOS',
        'Brooklyn Nets': 'BKN',
        'Charlotte Hornets': 'CHA',
        'Chicago Bulls': 'CHI',
        'Cleveland Cavaliers': 'CLE',
        'Dallas Mavericks': 'DAL',
        'Denver Nuggets': 'DEN',
        'Detroit Pistons': 'DET',
        'Golden State Warriors': 'GSW',
        'Houston Rockets': 'HOU',
        'Indiana Pacers': 'IND',
        'Los Angeles Clippers': 'LAC',
        'Los Angeles Lakers': 'LAL',
        'Memphis Grizzlies': 'MEM',
        'Miami Heat': 'MIA',
        'Milwaukee Bucks': 'MIL',
        'Minnesota Timberwolves': 'MIN',
        'New Orleans Pelicans': 'NOP',
        'New York Knicks': 'NYK',
        'Oklahoma City Thunder': 'OKC',
        'Orlando Magic': 'ORL',
        'Philadelphia 76ers': 'PHI',
        'Phoenix Suns': 'PHX',
        'Portland Trail Blazers': 'POR',
        'Sacramento Kings': 'SAC',
        'San Antonio Spurs': 'SAS',
        'Toronto Raptors': 'TOR',
        'Utah Jazz': 'UTA',
        'Washington Wizards': 'WAS'
    }
    
    # Intentar match
    logger.info("Haciendo match entre juegos de ESPN y NBA.com...")
    
    for espn_id, espn_data in tqdm(espn_games.items(), desc="Matching games"):
        home_team = espn_data['home_team']
        away_team = espn_data['away_team']
        
        # Convertir a tricodes
        home_tricode = TEAM_NAME_TO_TRICODE.get(home_team)
        away_tricode = TEAM_NAME_TO_TRICODE.get(away_team)
        
        if not home_tricode or not away_tricode:
            logger.warning(f"No se pudo convertir equipos: {away_team} @ {home_team} (ID: {espn_id})")
            unmatched_espn.append(espn_id)
            continue
        
        # Obtener scores de ESPN (asumiendo que están en 'home_score' y 'away_score' o en 'home_stats.PTS')
        # NOTA: Necesitamos cargar scores en load_espn_games también
        home_score = espn_data.get('home_score', 0)
        away_score = espn_data.get('away_score', 0)
        
        # Buscar en índice de NBA
        # Intento 1: Match exacto
        key = (away_tricode, home_tricode, away_score, home_score)
        
        if key in nba_index:
            mapping[espn_id] = nba_index[key]
            continue
            
        # Intento 2: Score invertido (ESPN a veces invierte home/away score o el orden)
        key_inverted = (away_tricode, home_tricode, home_score, away_score)
        
        if key_inverted in nba_index:
            mapping[espn_id] = nba_index[key_inverted]
            # logger.info(f"Match por score invertido: {espn_id}")
            continue
            
        unmatched_espn.append(espn_id)
    
    logger.success(f"✅ Match completado:")
    logger.info(f"  - Matched: {len(mapping)}")
    logger.info(f"  - ESPN sin match: {len(unmatched_espn)}")
    logger.info(f"  - NBA.com sin match: {len(nba_games) - len(mapping)}")
    
    return mapping, unmatched_espn

if __name__ == '__main__':
    print("="*80)
    print("SCRAPING COMPLETO DE NBA.COM SCHEDULE")
    print("="*80)
    
    # Paso 1: Scrapear schedule de NBA.com
    print("\n📅 Paso 1: Scrapeando schedule de NBA.com...")
    print("⚠️  ADVERTENCIA: Esto tomará ~2-3 horas (scraping de ~600 días)")
    print("Delay entre requests: 0.3 segundos\n")
    
    response = input("¿Continuar con scraping del schedule? (y/n): ")
    
    if response.lower() != 'y':
        print("Scraping cancelado")
        exit(0)
    
    nba_games = scrape_full_nba_schedule(delay=0.3)
    
    # Paso 2: Cargar juegos de ESPN
    print("\n📊 Paso 2: Cargando juegos de ESPN...")
    espn_games = load_espn_games()
    
    # Paso 3: Hacer match
    print("\n🔗 Paso 3: Haciendo match entre juegos...")
    mapping, unmatched = match_games(nba_games, espn_games)
    
    # Guardar mapping
    with open('data/espn_to_nba_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\n💾 Mapping guardado: data/espn_to_nba_mapping.json")
    
    # Guardar unmatched para revisión
    if unmatched:
        with open('data/unmatched_espn_games.json', 'w', encoding='utf-8') as f:
            json.dump(unmatched, f, indent=2)
        print(f"⚠️  Juegos sin match guardados: data/unmatched_espn_games.json")
    
    print(f"\n{'='*80}")
    print(f"RESUMEN FINAL")
    print(f"{'='*80}")
    print(f"NBA.com games: {len(nba_games)}")
    print(f"ESPN games: {len(espn_games)}")
    print(f"Matched: {len(mapping)}")
    print(f"Unmatched: {len(unmatched)}")
    print(f"{'='*80}")
