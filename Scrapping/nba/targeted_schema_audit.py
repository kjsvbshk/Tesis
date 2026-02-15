"""
Inspección focalizada de tablas clave
"""
from load_data import Config
import psycopg2

def audit_tables():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    # Tablas a inspeccionar
    target_tables = ['games', 'nba_player_boxscores', 'team_stats', 'player_stats']
    
    for table in target_tables:
        print(f"\n================ TABLE: {table} ================")
        
        # Columnas
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'espn' AND table_name = '{table}'
            ORDER BY ordinal_position;
        """)
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        
        print("Columns:")
        for name, dtype in cols:
            print(f"  - {name} ({dtype})")
            
        # Registros
        cur.execute(f"SELECT COUNT(*) FROM espn.{table}")
        count = cur.fetchone()[0]
        print(f"Total Rows: {count}")
        
        # Muestra de IDs
        id_candidates = ['game_id', 'id', 'espn_id']
        id_col = next((c for c in id_candidates if c in col_names), col_names[0])
        
        cur.execute(f"SELECT {id_col} FROM espn.{table} LIMIT 3")
        samples = [str(r[0]) for r in cur.fetchall()]
        print(f"Sample IDs ({id_col}): {samples}")

    conn.close()

if __name__ == '__main__':
    audit_tables()
