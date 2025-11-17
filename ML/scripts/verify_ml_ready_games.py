#!/usr/bin/env python3
"""Script para verificar la tabla ml_ready_games"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db_ml import MLDatabase
from sqlalchemy import text

db = MLDatabase()
with db.engine.connect() as conn:
    conn.execute(text(f"SET search_path TO {db.schema}, public"))
    conn.commit()
    
    # Check 1: Count
    result = conn.execute(text("SELECT COUNT(*) FROM ml.ml_ready_games"))
    count = result.fetchone()[0]
    print(f"✅ Check 1: Total de registros = {count}")
    assert count > 0, "La tabla debe tener al menos 1 registro"
    print()
    
    # Check 2: Muestra de datos
    print("✅ Check 2: Muestra de datos (primeros 5 registros):")
    result = conn.execute(text("""
        SELECT game_id, fecha, home_team, away_team, 
               home_score, away_score, home_win, point_diff
        FROM ml.ml_ready_games 
        ORDER BY fecha DESC 
        LIMIT 5
    """))
    rows = result.fetchall()
    
    for i, row in enumerate(rows, 1):
        print(f"   {i}. Game ID: {row[0]}, Fecha: {row[1]}")
        print(f"      {row[2]} vs {row[3]}, Score: {row[4]}-{row[5]}")
        print(f"      Home Win: {row[6]}, Point Diff: {row[7]}")
    print()
    
    # Check 3: Columnas disponibles
    result = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'ml' 
        AND table_name = 'ml_ready_games'
        ORDER BY ordinal_position
    """))
    columns = result.fetchall()
    print(f"✅ Check 3: Columnas disponibles ({len(columns)}):")
    for col in columns[:15]:
        print(f"   - {col[0]:<30} ({col[1]})")
    if len(columns) > 15:
        print(f"   ... y {len(columns) - 15} columnas más")
    print()
    
    print("=" * 60)
    print("✅ Todos los checks pasaron exitosamente")
    print("=" * 60)

