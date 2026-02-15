"""
Test del schedule scraper con validación de datos
"""

from nba_com.schedule_scraper import scrape_nba_schedule_for_date
import json

# Test con fecha reciente que sabemos tiene juegos
print("=== TEST 1: Scrapeando schedule del 13 de febrero 2026 ===\n")

games = scrape_nba_schedule_for_date('2026-02-13')

print(f"\n{'='*80}")
print(f"Juegos encontrados: {len(games)}")
print(f"{'='*80}\n")

if games:
    print("Primeros 5 juegos:")
    for i, game in enumerate(games[:5], 1):
        print(f"\n{i}. {game['nba_game_id']}")
        print(f"   {game['away_team']} ({game['away_tricode']}) @ {game['home_team']} ({game['home_tricode']})")
        print(f"   Status: {game['game_status_text']}")
        print(f"   Season Type: {game.get('season_type', 'N/A')}")
    
    # Guardar para inspección
    with open('test_schedule_games.json', 'w', encoding='utf-8') as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Datos guardados en: test_schedule_games.json")
    
    # Validar que todos tengan game_id
    missing_id = [g for g in games if not g.get('nba_game_id')]
    if missing_id:
        print(f"\n⚠️  WARNING: {len(missing_id)} juegos sin game_id")
    else:
        print(f"\n✅ Todos los juegos tienen game_id")
    
    # Validar que todos tengan equipos
    missing_teams = [g for g in games if not g.get('home_team') or not g.get('away_team')]
    if missing_teams:
        print(f"⚠️  WARNING: {len(missing_teams)} juegos sin equipos completos")
    else:
        print(f"✅ Todos los juegos tienen equipos")
        
else:
    print("❌ No se encontraron juegos - revisar estructura JSON")
