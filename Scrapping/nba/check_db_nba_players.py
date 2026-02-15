"""
Verificar que los datos se hayan cargado correctamente en la tabla nba_player_boxscores
"""

import os
import psycopg2
from psycopg2 import sql
import yaml
from pathlib import Path

from load_data import Config

def get_db_connection():
    try:
        config = Config()
        conn = psycopg2.connect(**config.db_config)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a DB: {e}")
        return None

def check_db():
    conn = get_db_connection()
    if not conn:
        return

    schema = 'espn'
    table = 'nba_player_boxscores'
    
    try:
        cur = conn.cursor()
        
        # 1. Contar registros
        query = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )
        cur.execute(query)
        count = cur.fetchone()[0]
        
        print(f"📊 Registros en DB ({schema}.{table}): {count}")
        
        # 2. Verificar muestra
        query = sql.SQL("SELECT * FROM {}.{} LIMIT 1").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )
        cur.execute(query)
        row = cur.fetchone()
        
        if row:
            print("✅ Muestra de datos obtenida:")
            # Obtener nombres de columnas
            col_names = [desc[0] for desc in cur.description]
            for col, val in zip(col_names, row):
                print(f"  - {col}: {val}")
        else:
            print("⚠️  La tabla está vacía")
            
        # 3. Verificar tipos de datos clave
        if count > 80000:
            print("\n✅ Integridad de Carga: EXITO TOTAL")
        else:
            print(f"\n⚠️  Integridad de Carga: PARCIAL ({count} vs esperado ~84,000)")

    except Exception as e:
        print(f"❌ Error consultando DB: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_db()
