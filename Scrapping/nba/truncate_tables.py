import psycopg2
from load_data import Config

def truncate_metadata_tables():
    config = Config()
    try:
        conn = psycopg2.connect(**config.db_config)
        cur = conn.cursor()
        
        tables = ['espn.standings', 'espn.team_stats', 'espn.odds']
        
        for table in tables:
            print(f"🧹 Truncating {table}...")
            # CASCADE to handle potential foreign keys (though we mostly use loose coupling)
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
            
        conn.commit()
        print("✅ Tables truncated successfully.")
        
    except Exception as e:
        print(f"❌ Error truncating tables: {e}")
        conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    truncate_metadata_tables()
