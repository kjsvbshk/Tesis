"""
Script de corrección de integridad y creación de tabla de mapping.
1. Normaliza game_id en nba_player_boxscores (agrega '00' faltante).
2. Crea tabla espn.game_id_mapping.
3. Carga datos del mapping JSON a la tabla.
"""
import json
import psycopg2
from load_data import Config
from pathlib import Path

def fix_and_map():
    print("🔧 Iniciando reparación de integridad y mapping...\n")
    
    config = Config()
    try:
        conn = psycopg2.connect(**config.db_config)
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return

    # 1. Normalizar IDs en nba_player_boxscores
    print("1️⃣  Normalizando IDs en 'nba_player_boxscores' (LPAD 10)...")
    try:
        # Verificar longitud actual
        cur.execute("SELECT game_id FROM espn.nba_player_boxscores LIMIT 1")
        sample = cur.fetchone()[0]
        print(f"   Muestra antes: '{sample}'")
        
        # Update masivo
        cur.execute("""
            UPDATE espn.nba_player_boxscores
            SET game_id = LPAD(game_id, 10, '0')
            WHERE LENGTH(game_id) < 10;
        """)
        updated = cur.rowcount
        conn.commit()
        print(f"   ✅ {updated} registros actualizados (padding '00').")
        
    except Exception as e:
        print(f"   ❌ Error actualizando IDs: {e}")
        conn.rollback()

    # 2. Crear tabla de Mapping
    print("\n2️⃣  Creando tabla 'espn.game_id_mapping'...")
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS espn.game_id_mapping (
                espn_id VARCHAR(15) PRIMARY KEY,
                nba_id VARCHAR(15) NOT NULL,
                season VARCHAR(10)
            );
            CREATE INDEX IF NOT EXISTS idx_mapping_nba ON espn.game_id_mapping(nba_id);
        """)
        conn.commit()
        print("   ✅ Tabla creada.")
        
    except Exception as e:
        print(f"   ❌ Error creando tabla: {e}")
        conn.rollback()

    # 3. Cargar Mapping
    print("\n3️⃣  Cargando datos de mapping...")
    try:
        mapping_path = Path('data/espn_to_nba_mapping.json')
        with open(mapping_path, 'r') as f:
            mapping = json.load(f)
            
        data = [(k, v) for k, v in mapping.items()]
        
        # Upsert (Insert or Do Nothing)
        args_str = ','.join(cur.mogrify("(%s, %s)", x).decode('utf-8') for x in data)
        
        cur.execute(f"""
            INSERT INTO espn.game_id_mapping (espn_id, nba_id)
            VALUES {args_str}
            ON CONFLICT (espn_id) DO NOTHING;
        """)
        inserted = cur.rowcount
        conn.commit()
        print(f"   ✅ {inserted} mapeos insertados.")
        
    except Exception as e:
        print(f"   ❌ Error insertando mapping: {e}")
        conn.rollback()

    print("\n4️⃣  Poblando columna 'season' desde espn.games (calculado desde fecha)...")
    try:
        # Calcular season basado en fecha:
        # Si mes >= 10, season = YYYY-(YY+1)
        # Si mes < 10, season = (YYYY-1)-YY
        cur.execute("""
            UPDATE espn.game_id_mapping m
            SET season = CASE 
                WHEN EXTRACT(MONTH FROM g.fecha) >= 10 THEN 
                    TO_CHAR(g.fecha, 'YYYY') || '-' || TO_CHAR(g.fecha + INTERVAL '1 year', 'YY')
                ELSE 
                    TO_CHAR(g.fecha - INTERVAL '1 year', 'YYYY') || '-' || TO_CHAR(g.fecha, 'YY')
            END
            FROM espn.games g
            WHERE m.espn_id = g.game_id::text
            AND m.season IS NULL;
        """)
        updated_seasons = cur.rowcount
        conn.commit()
        print(f"   ✅ {updated_seasons} temporadas actualizadas.")
    except Exception as e:
        print(f"   ❌ Error actualizando temporadas: {e}")
        conn.rollback()

    conn.close()
    print("\n✨ Proceso de integridad finalizado.")

if __name__ == '__main__':
    fix_and_map()
