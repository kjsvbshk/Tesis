import psycopg2
from load_data import Config

def inspect():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    print("🔍 Inspecting game_id columns...")
    
    # Check Types
    cur.execute("""
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'espn' 
          AND column_name = 'game_id' 
          AND table_name IN ('games', 'nba_player_boxscores')
    """)
    for row in cur.fetchall():
        print(f"Type Info: {row}")
        
    # Check Samples
    print("\n📋 Sample Values:")
    cur.execute("SELECT game_id FROM espn.games LIMIT 3")
    print(f"Games (espn.games): {cur.fetchall()}")
    
    cur.execute("SELECT game_id FROM espn.nba_player_boxscores LIMIT 3")
    print(f"Boxscores (espn.nba_player_boxscores): {cur.fetchall()}")
    
    conn.close()

if __name__ == "__main__":
    inspect()
