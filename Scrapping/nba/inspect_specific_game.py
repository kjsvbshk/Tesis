import psycopg2
from load_data import Config

def inspect():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    print("🔍 Inspecting Pacers games...")
    query = """
        SELECT game_id, fecha, home_team, away_team 
        FROM espn.games 
        WHERE fecha >= '2025-10-20' AND fecha <= '2025-10-30'
        AND (home_team ILIKE '%Pacers%' OR away_team ILIKE '%Pacers%')
    """
    cur.execute(query)
    rows = cur.fetchall()
    
    if not rows:
        print("❌ No Pacers games found in range 2025-10-20 to 2025-10-30")
    else:
        for r in rows:
            print(f"   {r}")
            
    conn.close()

if __name__ == "__main__":
    inspect()
