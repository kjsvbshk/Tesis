"""
Script de debug para el matching de juegos
"""

import json
import os
from loguru import logger
from tqdm import tqdm

def load_nba_schedule(file_path='data/nba_com_schedule.json'):
    print(f"Cargando schedule de {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        games = json.load(f)
    print(f"✅ Cargados {len(games)} juegos de NBA.com")
    
    # Mostrar muestra de equipos
    teams = set()
    for g in games[:50]:
        teams.add(f"{g.get('away_team')} ({g.get('away_tricode')})")
    print(f"\nEjemplos de equipos en NBA.com: {list(teams)[:5]}")
    
    return games

def load_espn_games(boxscores_dir='data/raw/boxscores'):
    print(f"\nCargando juegos de ESPN desde {boxscores_dir}...")
    
    espn_games = {}
    files = [f for f in os.listdir(boxscores_dir) if f.endswith('.json')]
    
    # Muestrear primeros 5 para debug
    print("\nRevisando primeros 5 archivos de ESPN:")
    
    for filename in files[:5]:
        path = os.path.join(boxscores_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  File: {filename}")
            print(f"    Home: '{data.get('home_team')}'")
            print(f"    Away: '{data.get('away_team')}'")
            print(f"    Date: '{data.get('fecha')}'")
            
        espn_games[filename.replace('.json', '')] = {
            'fecha': data.get('fecha'),
            'home_team': data.get('home_team'),
            'away_team': data.get('away_team')
        }
    
    # Cargar el resto
    print(f"\nCargando {len(files)} archivos total...")
    count_none = 0
    for filename in files:
        if filename.replace('.json', '') in espn_games: continue
        
        path = os.path.join(boxscores_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            home = data.get('home_team')
            away = data.get('away_team')
            
            if not home or not away:
                count_none += 1
                if count_none <= 5:
                    print(f"⚠️  WARNING: Teams None en {filename}: Home='{home}', Away='{away}'")
            
            espn_games[filename.replace('.json', '')] = {
                'fecha': data.get('fecha'),
                'home_team': home,
                'away_team': away
            }
        except Exception as e:
            print(f"Error en {filename}: {e}")
            
    print(f"Total juegos con equipos None: {count_none}")
    return espn_games

def match_debug(nba_games, espn_games):
    print("\nIniciando match debug...")
    
    # Crear índice NBA
    nba_index = {}
    for game in nba_games:
        # Normalizar fecha
        date = game.get('date').split('T')[0] # Asegurar formato YYYY-MM-DD
        key = (date, game.get('away_tricode'), game.get('home_tricode'))
        nba_index[key] = game.get('nba_game_id')
        
    print(f"Índice NBA creado con {len(nba_index)} claves")
    print(f"Ejemplo clave NBA: {list(nba_index.keys())[0]}")
    
    # Mapping ESPN names
    TEAM_NAME_TO_TRICODE = {
        'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 
        'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 
        'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET', 
        'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND', 
        'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 
        'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 
        'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 
        'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX', 
        'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 
        'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
    }
    
    matched = 0
    failed = 0
    
    for espn_id, data in list(espn_games.items())[:20]: # Probar primeros 20
        home = data['home_team']
        away = data['away_team']
        fecha = data['fecha']
        
        home_tri = TEAM_NAME_TO_TRICODE.get(home)
        away_tri = TEAM_NAME_TO_TRICODE.get(away)
        
        print(f"\nIntento match {espn_id}:")
        print(f"  ESPN: {fecha} {away} ({away_tri}) @ {home} ({home_tri})")
        
        if not home_tri or not away_tri:
            print(f"  ❌ Falló conversión tricode")
            continue
            
        key = (fecha, away_tri, home_tri)
        if key in nba_index:
            print(f"  ✅ MATCH! NBA ID: {nba_index[key]}")
            matched += 1
        else:
            print(f"  ❌ No encontrado en índice NBA")
            # Buscar fechas cercanas o invertir localia para debug
            found_partial = False
            for k in nba_index:
                if k[1] == away_tri and k[2] == home_tri:
                    print(f"    -> Encontrado en otra fecha: {k[0]}")
                    found_partial = True
                    break
            if not found_partial:
                print("    -> No se encontró ese matchup en ninguna fecha")

if __name__ == '__main__':
    nba_games = load_nba_schedule()
    espn_games = load_espn_games()
    match_debug(nba_games, espn_games)
