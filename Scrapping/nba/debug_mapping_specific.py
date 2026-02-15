import psycopg2
from load_data import Config

def debug_specific():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    print("🕵️ Debugging Specific Game Date Corruption...")
    
    # 1. Find a corrupted game in espn.games
    cur.execute("SELECT game_id, home_team, away_team FROM espn.games WHERE fecha = '2025-11-09' LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("No corrupted games found? That's unexpected given previous output.")
        return
        
    espn_id, home, away = row
    print(f"\n1. Corrupted Game in espn.games:")
    print(f"   ID: {espn_id} | {home} vs {away} | Date: 2025-11-09")
    
    # 2. Check Mapping
    cur.execute("SELECT nba_id, season FROM espn.game_id_mapping WHERE espn_id = %s", (str(espn_id),))
    map_row = cur.fetchone()
    print(f"\n2. Mapping for ESPN ID {espn_id}:")
    if map_row:
        nba_id = map_row[0]
        print(f"   NBA ID: {nba_id} | Season: {map_row[1]}")
    else:
        print("   ❌ NO MAPPING FOUND!")
        nba_id = None
        
    # 3. Check Source Boxscores
    if nba_id:
        print(f"\n3. Boxscores for NBA ID {nba_id}:")
        # Check both variants if needed?
        cur.execute("SELECT DISTINCT game_date, game_id FROM espn.nba_player_boxscores WHERE game_id = %s OR game_id = %s", (nba_id, "00"+nba_id))
        rows = cur.fetchall()
        for r in rows:
            print(f"   {r}")
            
    conn.close()

if __name__ == "__main__":
    debug_specific()
