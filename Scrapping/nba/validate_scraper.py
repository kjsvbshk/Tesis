from espn.espn_scraper import scrape_boxscore
import json

# Test with multiple recent games to validate extraction
test_games = [
    "401704650",  # Warriors vs Jazz (Oct 25, 2024)
    "401584089",  # Cavaliers @ Pacers
    "401584090",  # Another recent game
]

print("=== VALIDACIÓN COMPLETA DE EXTRACCIÓN ===\n")

all_valid = True
for game_id in test_games:
    print(f"Testing game {game_id}...")
    result = scrape_boxscore(game_id)
    
    if not result:
        print(f"  ❌ FAILED: No result returned\n")
        all_valid = False
        continue
    
    # Check teams and scores
    has_teams = result.get('home_team') and result.get('away_team')
    has_scores = result.get('home_score') is not None and result.get('away_score') is not None
    
    # Check stats
    home_stats = result.get('home_stats', {})
    away_stats = result.get('away_stats', {})
    
    required_stats = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'FG%', '3P%', 'FT%']
    
    home_complete = all(home_stats.get(stat) is not None for stat in required_stats)
    away_complete = all(away_stats.get(stat) is not None for stat in required_stats)
    
    print(f"  Teams: {'✅' if has_teams else '❌'} {result.get('away_team')} @ {result.get('home_team')}")
    print(f"  Scores: {'✅' if has_scores else '❌'} {result.get('away_score')}-{result.get('home_score')}")
    print(f"  Home Stats: {'✅' if home_complete else '❌'} {len([k for k,v in home_stats.items() if v is not None])}/{len(required_stats)} complete")
    print(f"  Away Stats: {'✅' if away_complete else '❌'} {len([k for k,v in away_stats.items() if v is not None])}/{len(required_stats)} complete")
    
    if home_complete and away_complete:
        print(f"  Sample home stats: PTS={home_stats['PTS']}, REB={home_stats['REB']}, AST={home_stats['AST']}, FG%={home_stats['FG%']}")
        print(f"  Sample away stats: PTS={away_stats['PTS']}, REB={away_stats['REB']}, AST={away_stats['AST']}, FG%={away_stats['FG%']}")
    else:
        print(f"  ⚠️  Missing stats:")
        for stat in required_stats:
            if home_stats.get(stat) is None:
                print(f"    Home {stat}: NULL")
            if away_stats.get(stat) is None:
                print(f"    Away {stat}: NULL")
        all_valid = False
    
    print()

if all_valid:
    print("✅ VALIDACIÓN EXITOSA - Todos los datos se extraen correctamente")
    print("✅ Listo para re-scrapear los 2,651 boxscores")
else:
    print("❌ VALIDACIÓN FALLIDA - Hay datos faltantes")
    print("⚠️  NO proceder con re-scraping hasta corregir")
