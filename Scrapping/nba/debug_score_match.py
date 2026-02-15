"""
Investigar por qué falló el matching por scores
"""

import json

def investigate_mismatch():
    # Cargar schedule
    with open('data/nba_com_schedule.json', 'r', encoding='utf-8') as f:
        nba_games = json.load(f)
        
    print(f"Cargados {len(nba_games)} juegos del schedule")
    
    # Buscar CLE @ IND
    targets = []
    for g in nba_games:
        if g['away_tricode'] == 'CLE' and g['home_tricode'] == 'IND':
            targets.append(g)
            
    print(f"\nEncontrados {len(targets)} juegos CLE @ IND en NBA.com:")
    for g in targets:
        print(f"  Date: {g['date']}")
        print(f"  Score: {g['away_score']} - {g['home_score']}")
        print(f"  ID: {g['nba_game_id']}")
        
    # Verificar datos de ESPN para 401584089 (el ejemplo que falló)
    espn_id = '401584089'
    with open(f'data/raw/boxscores/{espn_id}.json', 'r', encoding='utf-8') as f:
        espn_data = json.load(f)
        
    print(f"\nDatos ESPN ({espn_id}):")
    print(f"  Matchup: {espn_data.get('away_team')} @ {espn_data.get('home_team')}")
    print(f"  Score: {espn_data.get('away_score')} - {espn_data.get('home_score')}")
    
    # Comparar tipos
    print(f"\nTipos de datos:")
    print(f"  NBA Away Score: {type(targets[0]['away_score'])} (Valor: {targets[0]['away_score']})")
    print(f"  ESPN Away Score: {type(espn_data.get('away_score'))} (Valor: {espn_data.get('away_score')})")

if __name__ == '__main__':
    investigate_mismatch()
