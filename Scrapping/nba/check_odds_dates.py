import psycopg2
from load_data import Config

def check():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    print("📅 Checking Odds Dates...")
    cur.execute("""
        SELECT (commence_time::TIMESTAMPTZ AT TIME ZONE 'US/Eastern')::date as game_date, count(*) 
        FROM espn.odds 
        GROUP BY 1 
        ORDER BY 1
    """)
    rows = cur.fetchall()
    print(f"Distribution: {rows}")
    
    print("\n📅 Checking Games Dates around Odds...")
    if rows:
        min_date = rows[0][0]
        max_date = rows[-1][0]
        cur.execute("SELECT fecha, count(*) FROM espn.games WHERE fecha BETWEEN %s AND %s GROUP BY 1 ORDER BY 1", (min_date, max_date))
        print(f"Games in range: {cur.fetchall()}")
    
    conn.close()

if __name__ == "__main__":
    check()
