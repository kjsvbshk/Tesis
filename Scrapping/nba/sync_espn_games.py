import requests
import json
import os
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Build from individual components if full URL is missing
    db_host = os.getenv("NEON_DB_HOST")
    db_port = os.getenv("NEON_DB_PORT", "5432")
    db_name = os.getenv("NEON_DB_NAME")
    db_user = os.getenv("NEON_DB_USER")
    db_password = os.getenv("NEON_DB_PASSWORD")
    if all([db_host, db_name, db_user, db_password]):
        DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require"

# ESPN API Config
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def get_dates_to_sync(days_back=1, days_forward=7):
    """Generate a list of date strings for ESPN API"""
    start_date = datetime.now() - timedelta(days=days_back)
    date_list = []
    for i in range(days_back + days_forward + 1):
        curr = start_date + timedelta(days=i)
        date_list.append(curr.strftime("%Y%m%d"))
    return date_list

def fetch_espn_games(date_str):
    """Fetch games for a specific date from ESPN API"""
    url = f"{BASE_URL}?dates={date_str}&limit=100"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        games = []
        for event in data.get('events', []):
            game_id = event['id']
            date_full = event['date'] # 2023-10-24T23:30:00Z
            fecha = date_full.split('T')[0]
            
            comps = event['competitions'][0]['competitors']
            home = next(c for c in comps if c['homeAway'] == 'home')
            away = next(c for c in comps if c['homeAway'] == 'away')
            
            home_team = home['team']['displayName']
            away_team = away['team']['displayName']
            
            # Scores are usually null/0 for upcoming games
            home_score = home.get('score')
            away_score = away.get('score')
            
            # Parse scores as floats to match DB schema (DOUBLE PRECISION)
            try:
                home_score = float(home_score) if home_score is not None else None
            except:
                home_score = None
                
            try:
                away_score = float(away_score) if away_score is not None else None
            except:
                away_score = None

            games.append((
                int(game_id),
                fecha,
                home_team,
                away_team,
                home_score,
                away_score
            ))
        return games
    except Exception as e:
        print(f"[ERROR] Error fetching {date_str}: {e}")
        return []

def sync_to_db(games):
    """Upsert games into espn.games table"""
    if not games:
        print("[INFO] No games to sync.")
        return

    if not DATABASE_URL:
        print("[ERROR] Error: DATABASE_URL not found.")
        return

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # SQL for UPSERT
        # We only update fecha, teams and scores. We don't want to overwrite 
        # complex stats if they already exist from previous ETLs.
        upsert_query = """
            INSERT INTO espn.games (game_id, fecha, home_team, away_team, home_score, away_score)
            VALUES %s
            ON CONFLICT (game_id) DO UPDATE SET
                fecha = EXCLUDED.fecha,
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team,
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score
        """
        
        execute_values(cur, upsert_query, games)
        conn.commit()
        print(f"[SUCCESS] Successfully synced {len(games)} games to database.")
        
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

def main():
    print("Starting Real-Time Game Sync...")
    dates = get_dates_to_sync()
    print(f"Syncing dates from {dates[0]} to {dates[-1]}...")
    
    all_synced_games = []
    for date_str in dates:
        print(f"   Fetching {date_str}...")
        games = fetch_espn_games(date_str)
        if games:
            all_synced_games.extend(games)
            
    sync_to_db(all_synced_games)
    print("Sync complete.")

if __name__ == "__main__":
    main()
