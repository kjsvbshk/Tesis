import requests
import json
import csv
import time
from datetime import datetime, timedelta
from pathlib import Path

# Config
OUTPUT_FILE = 'data/raw/espn_games_repaired.csv'
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

SEASON_RANGES = [
    ('2023-10-24', '2024-06-20'), # 2023-24 Season
    ('2024-10-22', '2025-06-30'), # 2024-25 Season
    ('2025-10-22', '2026-06-30')  # 2025-26 Season (Current)
]

def get_dates_between(start_str, end_str):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    date_list = []
    curr = start
    while curr <= end:
        date_list.append(curr.strftime("%Y%m%d"))
        curr += timedelta(days=1)
    return date_list

def scrape_schedule():
    print(f"🚀 Starting ESPN Schedule Scraper...")
    
    all_games = []
    seen_ids = set()
    
    # Create header
    fieldnames = ['game_id', 'fecha', 'home_team', 'away_team', 'home_score', 'away_score', 'status']
    
    # Date list
    dates_to_scrape = []
    for start, end in SEASON_RANGES:
        dates_to_scrape.extend(get_dates_between(start, end))
        
    print(f"📅 Scrapeando {len(dates_to_scrape)} días...")
    
    with requests.Session() as session:
        for i, date_str in enumerate(dates_to_scrape):
            try:
                # Progress
                if i % 10 == 0:
                    print(f"   Processing {date_str} ({i}/{len(dates_to_scrape)})... Found {len(all_games)} games.")
                    
                url = f"{BASE_URL}?dates={date_str}&limit=100"
                resp = session.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                for event in data.get('events', []):
                    game_id = event['id']
                    
                    if game_id in seen_ids:
                        continue
                    
                    # Extract Data
                    date_full = event['date'] # 2023-10-24T23:30:00Z
                    fecha = date_full.split('T')[0]
                    
                    status = event['status']['type']['name'] # STATUS_FINAL
                    
                    comps = event['competitions'][0]['competitors']
                    home = next(c for c in comps if c['homeAway'] == 'home')
                    away = next(c for c in comps if c['homeAway'] == 'away')
                    
                    home_team = home['team']['displayName']
                    away_team = away['team']['displayName']
                    home_score = home.get('score', 0)
                    away_score = away.get('score', 0)
                    
                    all_games.append({
                        'game_id': game_id,
                        'fecha': fecha,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_score': home_score,
                        'away_score': away_score,
                        'status': status
                    })
                    seen_ids.add(game_id)
                
                time.sleep(0.1) # Be nice
                
            except Exception as e:
                print(f"❌ Error on {date_str}: {e}")
                
    # Save to CSV
    print(f"\n💾 Saving {len(all_games)} games to {OUTPUT_FILE}...")
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_games)
        
    print("✅ Done.")

if __name__ == "__main__":
    scrape_schedule()
