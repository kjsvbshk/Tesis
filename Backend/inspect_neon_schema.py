"""
Script para inspeccionar la estructura real de las tablas en Neon
Muestra todas las columnas de las tablas en el esquema espn
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from app.core.config import settings

load_dotenv()

def inspect_schema():
    """Inspecciona la estructura real de las tablas en Neon"""
    print("🔍 INSPECCIÓN DE ESTRUCTURA DE BASE DE DATOS EN NEON\n")
    
    # Conectar a Neon usando la misma configuración que la app
    engine = create_engine(settings.NBA_DATABASE_URL)
    
    with engine.connect() as conn:
        # Establecer search_path
        conn.execute(text("SET search_path TO espn, public"))
        conn.commit()
        
        # Obtener todas las tablas en el esquema espn
        print("📋 TABLAS EN EL ESQUEMA 'espn':")
        tables_result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables 
            WHERE table_schema = 'espn'
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in tables_result.fetchall()]
        print(f"   Encontradas {len(tables)} tablas: {', '.join(tables)}\n")
        
        # Para cada tabla, mostrar sus columnas
        for table_name in tables:
            print(f"📊 TABLA: {table_name}")
            print("   " + "=" * 60)
            
            columns_result = conn.execute(text("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_schema = 'espn' AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})
            
            columns = columns_result.fetchall()
            
            if columns:
                print(f"   Columnas ({len(columns)}):")
                for col in columns:
                    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                    default = f" DEFAULT {col[3]}" if col[3] else ""
                    print(f"     - {col[0]:<30} {col[1]:<20} {nullable}{default}")
            else:
                print("   ⚠️  No se encontraron columnas")
            
            print()
        
        # Mostrar también información sobre índices
        print("\n🔑 ÍNDICES:")
        for table_name in tables:
            indexes_result = conn.execute(text("""
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE schemaname = 'espn' AND tablename = :table_name
            """), {"table_name": table_name})
            
            indexes = indexes_result.fetchall()
            if indexes:
                print(f"\n   Tabla: {table_name}")
                for idx in indexes:
                    print(f"     - {idx[0]}: {idx[1]}")

if __name__ == "__main__":
    try:
        inspect_schema()
        print("\n✅ Inspección completada")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

