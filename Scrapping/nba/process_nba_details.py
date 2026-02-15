"""
Procesa los archivos JSON de NBA.com players y genera un CSV consolidado para carga en BD.
"""

import json
import csv
import glob
import os
from tqdm import tqdm
from pathlib import Path

def process_nba_details():
    input_dir = Path('data/raw/nba_com_players')
    output_dir = Path('data/processed')
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / 'nba_player_boxscores.csv'
    
    files = list(input_dir.glob('*.json'))
    print(f"📂 Procesando {len(files)} archivos JSON...")
    # Cargar Schedule para obtener fechas
    schedule_path = Path('data/nba_com_schedule.json')
    game_dates = {}
    if schedule_path.exists():
        with open(schedule_path, 'r') as f:
            schedule = json.load(f)
            # Crear mapa game_id -> game_date_est (cortando fecha ISO)
            for game in schedule:
                if 'nba_game_id' in game and 'date' in game:
                    # nba_game_id ej: "0022300061", date: "2023-10-24"
                    gid = game['nba_game_id']
                    game_dates[gid] = game['date']
    
    # Definir columnas del CSV
    fieldnames = [
        'game_id', 'game_date', 'team_tricode', 'player_id', 'player_name', 
        'position', 'starter', 'minutes', 
        'pts', 'reb', 'ast', 'stl', 'blk', 'to', 'pf', 'plus_minus',
        'fgm', 'fga', 'fg_pct', 
        'three_pm', 'three_pa', 'three_pct', 
        'ftm', 'fta', 'ft_pct', 
        'oreb', 'dreb'
    ]
    
    # Stats vacías para jugadores que no jugaron (DNP) o inactivos si decidimos incluirlos
    # Por ahora solo procesaremos active players
    
    count = 0
    errors = 0
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for fpath in tqdm(files):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                game_id = data.get('game_id')
                if not game_id:
                    continue
                
                game_date = game_dates.get(game_id, '') # Obtener la fecha del juego
                
                # Procesar Home y Away
                for side in ['home', 'away']:
                    team_tricode = data.get(f'{side}_team_tricode')
                    players = data.get(f'{side}_players', [])
                    
                    for p in players:
                        # Campos base
                        row = {
                            'game_id': game_id,
                            'game_date': game_date,
                            'team_tricode': team_tricode, # Assuming team_code was a typo and should be team_tricode
                            'player_id': p.get('player_id'),
                            'player_name': p.get('player_name'),
                            'position': p.get('position', ''),
                            'starter': p.get('starter', False),
                            'minutes': p.get('minutes', ''),
                            
                            # Stats (usar 0 si es None o vacío)
                            'pts': int(p.get('pts') or 0),
                            'reb': int(p.get('reb') or 0),
                            'ast': int(p.get('ast') or 0),
                            'stl': int(p.get('stl') or 0),
                            'blk': int(p.get('blk') or 0),
                            'to': int(p.get('to') or 0),
                            'pf': int(p.get('pf') or 0),
                            'plus_minus': int(p.get('plus_minus') or 0),
                            
                            'fgm': int(p.get('fgm') or 0),
                            'fga': int(p.get('fga') or 0),
                            'fg_pct': float(p.get('fg_pct') or 0.0),
                            
                            'three_pm': int(p.get('three_pm') or 0),
                            'three_pa': int(p.get('three_pa') or 0),
                            'three_pct': float(p.get('three_pct') or 0.0),
                            
                            'ftm': int(p.get('ftm') or 0),
                            'fta': int(p.get('fta') or 0),
                            'ft_pct': float(p.get('ft_pct') or 0.0),
                            
                            'oreb': int(p.get('oreb') or 0),
                            'dreb': int(p.get('dreb') or 0)
                        }
                        
                        writer.writerow(row)
                        count += 1
                        
            except Exception as e:
                # print(f"Error en {fpath.name}: {e}")
                errors += 1
                
    print(f"✅ Procesamiento completado.")
    print(f"📊 Total registros generados: {count}")
    print(f"⚠️  Archivos con error: {errors}")
    print(f"💾 Guardado en: {output_file}")

if __name__ == '__main__':
    process_nba_details()
