"""
Resetear la tabla nba_player_boxscores para recargar con nueva columna de fecha.
"""
import psycopg2
from load_data import Config

def reset_table():
    print("🧹 Reseteando tabla nba_player_boxscores...")
    config = Config()
    try:
        conn = psycopg2.connect(**config.db_config)
        cur = conn.cursor()
        
        # Drop view first due to dependency
        print("   - Eliminando vista unified_player_boxscores...")
        cur.execute("DROP VIEW IF EXISTS espn.unified_player_boxscores CASCADE;")
        
        # Drop table
        print("   - Eliminando tabla nba_player_boxscores...")
        cur.execute("DROP TABLE IF EXISTS espn.nba_player_boxscores CASCADE;")
        
        conn.commit()
        print("✅ Tablas eliminadas. Listo para reload.")
        
    except Exception as e:
        print(f"❌ Error eliminando tablas: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    reset_table()
