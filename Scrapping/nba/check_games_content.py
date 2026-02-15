import psycopg2
from load_data import Config

def check_content():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    print("📅 Checking ESPN Games Content...")
    
    # 1. Check Date Distribution
    cur.execute("SELECT fecha, count(*) FROM espn.games GROUP BY 1 ORDER BY 1")
    rows = cur.fetchall()
    print(f"\nDistinct Dates Count: {len(rows)}")
    print("First 5 Dates:")
    for r in rows[:5]: print(f"   {r}")
    print("Last 5 Dates:")
    for r in rows[-5:]: print(f"   {r}")
    
    # 2. Check Specific Date (2025-10-24)
    target = '2025-10-24'
    print(f"\n🔍 Games on {target}:")
    cur.execute("SELECT game_id, fecha, home_team, away_team FROM espn.games WHERE fecha = %s", (target,))
    games = cur.fetchall()
    if not games:
        print("   ❌ NO GAMES FOUND via SQL query.")
    else:
        for g in games:
            print(f"   {g}")

    # 3. Check Team Names Sample
    print("\n🏀 Team Names Sample:")
    cur.execute("SELECT DISTINCT home_team FROM espn.games LIMIT 10")
    print(cur.fetchall())
            
    conn.close()

if __name__ == "__main__":
    check_content()
