#!/usr/bin/env python3
"""Script rápido para verificar el estado del esquema ML"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db_ml import MLDatabase
from sqlalchemy import text

db = MLDatabase()
with db.engine.connect() as conn:
    conn.execute(text(f"SET search_path TO {db.schema}, public"))
    conn.commit()
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'ml' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """))
    tables = [r[0] for r in result.fetchall()]
    
    print(f"📊 Estado del esquema ML:")
    print(f"   Tablas encontradas: {len(tables)}")
    if tables:
        print("   Tablas:")
        for t in tables:
            print(f"     - {t}")
    else:
        print("   ✅ Esquema limpio (sin tablas)")

