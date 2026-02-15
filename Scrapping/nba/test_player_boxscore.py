"""
Test del player boxscore scraper con game_id de NBA.com
"""

from nba_com.player_boxscore_scraper import scrape_player_boxscore
import json

# Usar uno de los game_ids del schedule
test_game_id = '0032500004'  # Team Austin @ Team Melo (All-Star)

print(f"=== TEST: Scrapeando player boxscore ===")
print(f"Game ID: {test_game_id}\n")

# Scrapear SIN team slugs (el game_id debería ser suficiente)
result = scrape_player_boxscore(test_game_id)

if result:
    print(f"\n{'='*80}")
    print(f"RESULTADO")
    print(f"{'='*80}")
    print(f"Away Team: {result['away_team']} ({result['away_team_tricode']})")
    print(f"  - Activos: {len(result['away_players'])}")
    print(f"  - Inactivos: {len(result['away_inactive'])}")
    
    print(f"\nHome Team: {result['home_team']} ({result['home_team_tricode']})")
    print(f"  - Activos: {len(result['home_players'])}")
    print(f"  - Inactivos: {len(result['home_inactive'])}")
    
    total_active = len(result['away_players']) + len(result['home_players'])
    total_inactive = len(result['away_inactive']) + len(result['home_inactive'])
    
    print(f"\n{'='*80}")
    print(f"VALIDACIÓN")
    print(f"{'='*80}")
    
    # Validar que tengamos jugadores
    if total_active > 0:
        print(f"✅ Total jugadores activos: {total_active}")
        
        # Mostrar primer jugador para validar stats
        if result['away_players']:
            first_player = result['away_players'][0]
            print(f"\n✅ Ejemplo - Primer jugador {result['away_team']}:")
            print(f"   Nombre: {first_player['player_name']}")
            print(f"   Posición: {first_player['position']}")
            print(f"   Minutos: {first_player['minutes']}")
            print(f"   Puntos: {first_player['pts']}")
            print(f"   Rebotes: {first_player['reb']}")
            print(f"   Asistencias: {first_player['ast']}")
            
            # Verificar que tenga las 20 stats
            expected_keys = ['player_name', 'player_id', 'position', 'starter', 'minutes', 
                           'fgm', 'fga', 'fg_pct', 'three_pm', 'three_pa', 'three_pct',
                           'ftm', 'fta', 'ft_pct', 'oreb', 'dreb', 'reb', 'ast', 'stl', 
                           'blk', 'to', 'pf', 'pts', 'plus_minus']
            
            missing_keys = [k for k in expected_keys if k not in first_player]
            if missing_keys:
                print(f"\n⚠️  WARNING: Faltan keys: {missing_keys}")
            else:
                print(f"\n✅ Todas las 24 keys presentes (20 stats + 4 metadata)")
    else:
        print(f"❌ No se encontraron jugadores activos")
    
    if total_inactive > 0:
        print(f"\n✅ Total jugadores inactivos: {total_inactive}")
        if result['away_inactive']:
            print(f"   Ejemplo: {result['away_inactive'][0]['player_name']}")
    else:
        print(f"\n⚠️  No hay jugadores inactivos (puede ser normal para All-Star)")
    
    # Guardar
    with open('test_player_boxscore.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Datos guardados en: test_player_boxscore.json")
    
else:
    print(f"\n❌ ERROR: No se pudo extraer el boxscore")
    print(f"   Verificar que el game_id sea correcto y que la página exista")
