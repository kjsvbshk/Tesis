"""
Verificar rango de fechas en la vista unificada y tabla base
"""
import psycopg2
from load_data import Config

def verify():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    # 1. Verificar Tabla Base
    print("--- nba_player_boxscores (Base) ---")
    cur.execute("SELECT MIN(game_date), MAX(game_date), COUNT(*) FROM espn.nba_player_boxscores")
    min_d, max_d, count = cur.fetchone()
    print(f"Rango: {min_d} a {max_d}")
    print(f"Total Registros: {count}")
    
    # 2. Verificar Vista Unificada
    print("\n--- unified_player_boxscores (Vista) ---")
    try:
        cur.execute("SELECT MIN(game_date), MAX(game_date), COUNT(*) FROM espn.unified_player_boxscores")
        min_v, max_v, count_v = cur.fetchone()
        print(f"Rango: {min_v} a {max_v}")
        print(f"Total Registros: {count_v}")
        
    except Exception as e:
        print(f"Error consultando vista: {e}")

    conn.close()

if __name__ == '__main__':
    verify()
