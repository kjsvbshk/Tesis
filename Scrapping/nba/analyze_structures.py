import psycopg2
from load_data import Config
import json
from datetime import datetime
import pytz

def analyze():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    target_date = '2025-10-24'
    
    with open('structure_analysis.txt', 'w', encoding='utf-8') as f:
        f.write(f"🔍 ANALYZING DATA STRUCTURES FOR DATE: {target_date}\n")
        f.write("="*60 + "\n")
        
        # 1. ESPN GAMES STRUCTURE
        f.write("\n🏀 ESPN GAMES (Target):\n")
        f.write(f"   Cols: game_id, fecha, home_team, away_team\n")
        cur.execute("""
            SELECT game_id, fecha, home_team, away_team 
            FROM espn.games 
            WHERE fecha = %s
            LIMIT 5
        """, (target_date,))
        games = cur.fetchall()
        for g in games:
            f.write(f"   Row: {g}\n")
            
        # 2. PROCESSED ODDS STRUCTURE
        f.write("\n🎲 RAW ODDS (Source):\n")
        f.write(f"   Cols: game_id, commence_time, home_team, away_team\n")
        # Note: We cast commence_time to date in US/Eastern to match game date
        cur.execute("""
            SELECT game_id, commence_time, home_team, away_team 
            FROM espn.odds 
            WHERE (commence_time::TIMESTAMPTZ AT TIME ZONE 'US/Eastern')::date = %s
            LIMIT 5
        """, (target_date,))
        odds = cur.fetchall()
        for o in odds:
            f.write(f"   Row: {o}\n")
        
    conn.close()

if __name__ == "__main__":
    analyze()
