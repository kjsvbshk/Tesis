import psycopg2
from load_data import Config

def fix_tables():
    print("🛠️ Fixing Odds Tables Schema...")
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    try:
        # 1. Drop existing tables
        print("🗑️ Dropping existing tables...")
        cur.execute("DROP TABLE IF EXISTS espn.odds_event_game_map CASCADE;")
        cur.execute("DROP TABLE IF EXISTS espn.game_odds CASCADE;")
        
        # 2. Create tables with correct schema
        print("🏗️ Creating tables...")
        
        # odds_event_game_map
        cur.execute("""
            CREATE TABLE espn.odds_event_game_map (
                odds_id TEXT PRIMARY KEY,
                game_id BIGINT
            );
        """)
        
        # game_odds
        cur.execute("""
            CREATE TABLE espn.game_odds (
                id SERIAL PRIMARY KEY,
                game_id BIGINT,
                odds_type TEXT,
                odds_value NUMERIC,
                line_value NUMERIC,
                provider TEXT,
                UNIQUE(game_id, odds_type, provider, line_value)
            );
        """)
        
        conn.commit()
        print("✅ Tables recreated successfully.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_tables()
