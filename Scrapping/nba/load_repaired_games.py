import pandas as pd
import psycopg2
from load_data import Config
import os

REPAIRED_FILE = 'data/raw/espn_games_repaired.csv'

def load_repaired():
    print("🚀 Loading Repaired Games...")
    
    if not os.path.exists(REPAIRED_FILE):
        print(f"❌ File not found: {REPAIRED_FILE}")
        return

    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    try:
        # 1. Delete (TRUNCATE can lock)
        print("🗑️ Deleting from espn.games...")
        cur.execute("DELETE FROM espn.games")
        conn.commit()
        
        # 2. Load CSV
        print(f"📖 Reading {REPAIRED_FILE}...")
        df = pd.read_csv(REPAIRED_FILE)
        print(f"   Rows to load: {len(df)}")
        
        # 3. Insert
        print("⬇️ Inserting data...")
        # Use copy_from or insert many
        # Since it's < 5000 rows, execute_batch is fine or just loop for simplicity/safety
        # Better: construct INSERT statement
        
        # Mapping DataFrame columns to Table columns
        # CSV: game_id, fecha, home_team, away_team, home_score, away_score, status
        # Table: game_id, fecha, home_team, away_team, home_score, away_score, status (and others nullable)
        
        # Prepare data
        data_tuples = [tuple(x) for x in df.to_numpy()]
        
        cols = ','.join(list(df.columns)) # game_id,fecha,home_team,away_team,home_score,away_score,status
        
        # Build query
        # VALUES %s is handled by execute_values
        query = f"INSERT INTO espn.games ({cols}) VALUES %s"
        
        from psycopg2.extras import execute_values
        execute_values(cur, query, data_tuples)
        conn.commit()
        print(f"✅ Successfully inserted rows.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    load_repaired()
