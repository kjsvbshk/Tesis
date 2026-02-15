import psycopg2
from load_data import Config

def diagnose():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    print("🕵️ Diagnosing Date Source...")
    
    # 1. Check NBA Player Boxscores Date Distribution
    print("\n📅 NBA Player Boxscores (Source) Distribution:")
    cur.execute("SELECT game_date, count(DISTINCT game_id) FROM espn.nba_player_boxscores GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
    rows = cur.fetchall()
    for r in rows: print(f"   {r}")
    
    # 2. Check Game ID Mapping
    print("\n🔗 Game ID Mapping Sample:")
    cur.execute("SELECT * FROM espn.game_id_mapping LIMIT 5")
    rows = cur.fetchall()
    for r in rows: print(f"   {r}")
    
    # 3. Check specific bad date in Source
    bad_date = '2025-11-09'
    print(f"\n🔍 Source Games on {bad_date}:")
    cur.execute("SELECT DISTINCT game_id FROM espn.nba_player_boxscores WHERE game_date = %s LIMIT 10", (bad_date,))
    rows = cur.fetchall()
    print(f"   Sample Game IDs: {rows}")
    
    conn.close()

if __name__ == "__main__":
    diagnose()
