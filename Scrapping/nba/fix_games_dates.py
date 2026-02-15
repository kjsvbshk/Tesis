import psycopg2
from load_data import Config

def fix_dates():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    print("🛠️ Fixing game dates...")
    
    try:
        sql = """
        UPDATE espn.games g 
        SET fecha = sub.game_date::date 
        FROM (
            SELECT m.espn_id, MIN(pb.game_date) as game_date 
            FROM espn.nba_player_boxscores pb 
            JOIN espn.game_id_mapping m ON pb.game_id = m.nba_id 
            GROUP BY m.espn_id
        ) sub 
        WHERE g.game_id::text = sub.espn_id;
        """
        cur.execute(sql)
        conn.commit()
        print(f"✅ Updated {cur.rowcount} rows in espn.games.")
        
        # Verify
        cur.execute("SELECT count(DISTINCT fecha) FROM espn.games")
        print(f"distinct dates: {cur.fetchone()[0]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_dates()
