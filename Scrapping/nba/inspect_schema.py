"""
Inspeccionar esquema actual de la base de datos
"""
from load_data import Config
import psycopg2

def inspect_schema():
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    # Listar tablas
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'espn'
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    print(f"Tablas en esquema 'espn': {tables}\n")
    
    for table in tables:
        print(f"--- Estructura de {table} ---")
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'espn' AND table_name = '{table}'
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()
        for col in columns:
            print(f"  {col[0]}: {col[1]}")
            
        # Contar registros
        cur.execute(f"SELECT COUNT(*) FROM espn.{table}")
        count = cur.fetchone()[0]
        print(f"  Registros: {count}\n")
        
        # Si es la tabla games o nba_player_boxscores, mostrar muestra de IDs
        if table in ['games', 'nba_player_boxscores']:
            id_col = 'game_id' if 'game_id' in [c[0] for c in columns] else columns[0][0]
            cur.execute(f"SELECT {id_col} FROM espn.{table} LIMIT 5")
            sample_ids = [str(row[0]) for row in cur.fetchall()]
            print(f"  Muestra de IDs ({id_col}): {sample_ids}\n")

    conn.close()

if __name__ == '__main__':
    inspect_schema()
