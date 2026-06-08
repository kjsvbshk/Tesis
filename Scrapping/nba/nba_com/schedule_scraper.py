"""
Scrapear schedule de NBA.com para obtener game_ids correctos

NBA.com tiene páginas de schedule por fecha que contienen los game_ids
Ejemplo: https://www.nba.com/games?date=2024-10-22
"""

import requests
import json
import re
from datetime import datetime, timedelta
from loguru import logger
from tqdm import tqdm
import time

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

def scrape_nba_schedule_for_date(date_str):
    """
    Scrapear schedule de NBA.com para una fecha específica
    
    Args:
        date_str: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        list de dicts con game info
    """
    url = f"https://www.nba.com/games?date={date_str}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Extraer __NEXT_DATA__
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
        
        if not match:
            logger.warning(f"No __NEXT_DATA__ found for {date_str}")
            return []
        
        next_data = json.loads(match.group(1))
        
        # Navegar a los juegos - estructura: gameCardFeed.modules[].cards[]
        page_props = next_data.get('props', {}).get('pageProps', {})
        game_card_feed = page_props.get('gameCardFeed', {})
        modules = game_card_feed.get('modules', [])
        
        games = []
        for module in modules:
            cards = module.get('cards', [])
            
            for card in cards:
                card_data = card.get('cardData', {})
                
                # Verificar que tenga gameId
                if not card_data.get('gameId'):
                    continue
                
                game_info = {
                    'nba_game_id': card_data.get('gameId'),
                    'game_code': card_data.get('gameCode'),
                    'date': date_str,
                    'home_team': card_data.get('homeTeam', {}).get('teamName'),
                    'home_tricode': card_data.get('homeTeam', {}).get('teamTricode'),
                    'home_score': safe_int(card_data.get('homeTeam', {}).get('score')),
                    'away_team': card_data.get('awayTeam', {}).get('teamName'),
                    'away_tricode': card_data.get('awayTeam', {}).get('teamTricode'),
                    'away_score': safe_int(card_data.get('awayTeam', {}).get('score')),
                    'game_status': card_data.get('gameStatus'),
                    'game_status_text': card_data.get('gameStatusText'),
                    'season_type': card_data.get('seasonType')
                }
                games.append(game_info)
        
        logger.success(f"✅ {date_str}: {len(games)} juegos")
        return games
        
    except Exception as e:
        logger.error(f"Error scrapeando {date_str}: {e}")
        return []

def scrape_season_schedule(start_date, end_date, delay=0.5):
    """
    Scrapear schedule completo para un rango de fechas
    
    Args:
        start_date: Fecha inicio 'YYYY-MM-DD'
        end_date: Fecha fin 'YYYY-MM-DD'
        delay: Segundos entre requests
        
    Returns:
        list de todos los juegos
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    all_games = []
    current = start
    
    dates = []
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    logger.info(f"Scrapeando schedule: {start_date} a {end_date} ({len(dates)} días)")
    
    for date_str in tqdm(dates, desc="Scrapeando schedule"):
        games = scrape_nba_schedule_for_date(date_str)
        all_games.extend(games)
        time.sleep(delay)
    
    return all_games

if __name__ == '__main__':
    # Test con una semana
    print("=== TEST: Scrapeando schedule de una semana ===\n")
    
    games = scrape_season_schedule('2024-10-22', '2024-10-28', delay=0.5)
    
    print(f"\n{'='*80}")
    print(f"Total juegos encontrados: {len(games)}")
    print(f"{'='*80}\n")
    
    if games:
        print("Primeros 5 juegos:")
        for game in games[:5]:
            print(f"  {game['nba_game_id']}: {game['away_tricode']} @ {game['home_tricode']} ({game['date']})")
        
        # Guardar
        with open('nba_schedule_test.json', 'w', encoding='utf-8') as f:
            json.dump(games, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Guardado en: nba_schedule_test.json")
