"""
NBA.com Player Boxscore Scraper (usando __NEXT_DATA__)

NBA.com es una app Next.js que embebe los datos en un JSON dentro del HTML.
Extraemos el JSON directamente sin necesidad de renderizar JavaScript.
"""

import requests
import json
import os
import re
from loguru import logger
from typing import Optional, Dict, List

def scrape_player_boxscore(nba_com_game_id: str, away_slug: Optional[str] = None, home_slug: Optional[str] = None) -> Optional[Dict]:
    """
    Scrapear boxscore de jugadores desde NBA.com usando __NEXT_DATA__
    
    Args:
        nba_com_game_id: ID del partido en formato NBA.com (ej: '0022500778')
        away_slug: Slug del equipo visitante (ej: 'chi')
        home_slug: Slug del equipo local (ej: 'bos')
        
    Returns:
        dict con datos de jugadores de ambos equipos e inactivos
    """
    # Formato URL: chi-vs-bos-0022500778
    if away_slug and home_slug:
        game_slug = f"{away_slug}-vs-{home_slug}-{nba_com_game_id}"
    else:
        game_slug = nba_com_game_id
    
    url = f"https://www.nba.com/game/{game_slug}/box-score"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        logger.info(f"Scrapeando player boxscore: {game_slug}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Extraer __NEXT_DATA__ JSON
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
        
        if not match:
            logger.error(f"No se encontró __NEXT_DATA__ en {game_slug}")
            return None
        
        next_data = json.loads(match.group(1))
        
        # Navegar al boxscore data
        try:
            props = next_data['props']['pageProps']
            game = props.get('game', {})
            
            # Información básica del partido
            game_id = game.get('gameId', nba_com_game_id)
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})
            
            # Extraer player stats
            home_players_data = extract_players_from_team(home_team, 'home')
            away_players_data = extract_players_from_team(away_team, 'away')
            
            result = {
                'game_id': game_id,
                'away_team': away_team.get('teamName', 'Unknown'),
                'away_team_tricode': away_team.get('teamTricode', ''),
                'away_players': away_players_data['active'],
                'away_inactive': away_players_data['inactive'],
                'home_team': home_team.get('teamName', 'Unknown'),
                'home_team_tricode': home_team.get('teamTricode', ''),
                'home_players': home_players_data['active'],
                'home_inactive': home_players_data['inactive']
            }
            
            total_players = len(result['away_players']) + len(result['home_players'])
            total_inactive = len(result['away_inactive']) + len(result['home_inactive'])
            
            logger.success(f"✅ {away_team.get('teamTricode')} @ {home_team.get('teamTricode')}: {total_players} activos, {total_inactive} inactivos")
            
            return result
            
        except (KeyError, TypeError) as e:
            logger.error(f"Error parseando __NEXT_DATA__ structure: {e}")
            # Guardar para debug
            with open(f'debug_{nba_com_game_id}.json', 'w') as f:
                json.dump(next_data, f, indent=2)
            logger.info(f"Datos guardados en debug_{nba_com_game_id}.json")
            return None
        
    except requests.RequestException as e:
        logger.error(f"Error de conexión para {game_slug}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado para {game_slug}: {e}")
        return None

def extract_players_from_team(team_data: Dict, team_type: str) -> Dict[str, List]:
    """
    Extraer jugadores activos e inactivos de un equipo
    
    Args:
        team_data: Datos del equipo desde __NEXT_DATA__
        team_type: 'home' o 'away'
        
    Returns:
        dict con 'active' e 'inactive' lists
    """
    active_players = []
    inactive_players = []
    
    # Extraer jugadores activos
    players = team_data.get('players', [])
    
    for player in players:
        player_name = f"{player.get('firstName', '')} {player.get('familyName', '')}".strip()
        
        # Extraer estadísticas con fallback seguro
        stats = player.get('statistics', {})
        
        # Validar si stats es None (puede pasar en datos corruptos)
        if stats is None:
            stats = {}
        
        # Jugador activo con stats
        player_data = {
            'player_name': player_name,
            'player_id': str(player.get('personId', '')),  # Asegurar string
            'position': player.get('position', ''),
            'starter': str(player.get('starter', '0')) == '1',
            'minutes': str(stats.get('minutes', '0:00')),
            'fgm': safe_int(stats.get('fieldGoalsMade')),
            'fga': safe_int(stats.get('fieldGoalsAttempted')),
            'fg_pct': safe_float(stats.get('fieldGoalsPercentage')),
            'three_pm': safe_int(stats.get('threePointersMade')),
            'three_pa': safe_int(stats.get('threePointersAttempted')),
            'three_pct': safe_float(stats.get('threePointersPercentage')),
            'ftm': safe_int(stats.get('freeThrowsMade')),
            'fta': safe_int(stats.get('freeThrowsAttempted')),
            'ft_pct': safe_float(stats.get('freeThrowsPercentage')),
            'oreb': safe_int(stats.get('reboundsOffensive')),
            'dreb': safe_int(stats.get('reboundsDefensive')),
            'reb': safe_int(stats.get('reboundsTotal')),
            'ast': safe_int(stats.get('assists')),
            'stl': safe_int(stats.get('steals')),
            'blk': safe_int(stats.get('blocks')),
            'to': safe_int(stats.get('turnovers')),
            'pf': safe_int(stats.get('foulsPersonal')),
            'pts': safe_int(stats.get('points')),
            'plus_minus': safe_int(stats.get('plusMinusPoints'))
        }
        
        active_players.append(player_data)
    
    # Extraer jugadores inactivos
    inactives = team_data.get('inactives', [])
    if inactives is None:
        inactives = []
    
    for inactive in inactives:
        player_name = f"{inactive.get('firstName', '')} {inactive.get('familyName', '')}".strip()
        
        inactive_players.append({
            'player_name': player_name,
            'player_id': str(inactive.get('personId', '')),
            'jersey_num': str(inactive.get('jerseyNum', '')).strip()
        })
    
    return {
        'active': active_players,
        'inactive': inactive_players
    }

def safe_int(value) -> int:
    """Convertir a int de forma segura"""
    if value is None or value == '':
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0

def safe_float(value) -> float:
    """Convertir a float de forma segura"""
    if value is None or value == '':
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def save_player_boxscore(data: Dict, output_dir: str = 'data/raw/nba_com_players'):
    """
    Guardar boxscore de jugadores en JSON
    
    Args:
        data: Datos del boxscore
        output_dir: Directorio de salida
    """
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{output_dir}/{data['game_id']}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 Guardado: {filename}")

if __name__ == '__main__':
    # Test con el partido Bulls vs Celtics
    test_game_id = '0022500778'
    
    result = scrape_player_boxscore(test_game_id, away_slug='chi', home_slug='bos')
    
    if result:
        save_player_boxscore(result)
        
        # Mostrar resumen
        print(f"\n{'='*80}")
        print(f"GAME: {result['away_team']} @ {result['home_team']}")
        print(f"{'='*80}")
        print(f"\n{result['away_team']} ({result['away_team_tricode']}):")
        print(f"  - Activos: {len(result['away_players'])}")
        print(f"  - Inactivos: {len(result['away_inactive'])}")
        print(f"\n{result['home_team']} ({result['home_team_tricode']}):")
        print(f"  - Activos: {len(result['home_players'])}")
        print(f"  - Inactivos: {len(result['home_inactive'])}")
        
        # Mostrar primer jugador como ejemplo
        if result['away_players']:
            print(f"\nEjemplo - Primer jugador {result['away_team']}:")
            print(json.dumps(result['away_players'][0], indent=2))
