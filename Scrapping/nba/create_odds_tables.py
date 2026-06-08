import psycopg2
from load_data import Config

def create_tables():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    print("🛠️ Creating tables...")
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS espn.odds_event_game_map (
                odds_id TEXT PRIMARY KEY,
                game_id BIGINT
            );
            
            CREATE TABLE IF NOT EXISTS espn.game_odds (
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
        print("✅ Tables created successfully.")
        
        # Verify
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'espn' AND table_name IN ('odds_event_game_map', 'game_odds')")
        print(f"Existing tables: {cur.fetchall()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()
