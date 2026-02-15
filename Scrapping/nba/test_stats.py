from espn.espn_scraper import scrape_boxscore
import json

# Test with a recent game
game_id = "401704650"
result = scrape_boxscore(game_id)

print("=== SCRAPE RESULT ===")
print(json.dumps(result, indent=2))

print("\n=== STATS CHECK ===")
print(f"home_stats: {result.get('home_stats')}")
print(f"away_stats: {result.get('away_stats')}")
print(f"home_stats empty: {not result.get('home_stats')}")
print(f"away_stats empty: {not result.get('away_stats')}")
