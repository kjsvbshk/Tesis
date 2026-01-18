#!/usr/bin/env python3
"""
Script para ejecutar la migración de índices de rendimiento
"""

import sys
import os
from sqlalchemy import create_engine, text
from pathlib import Path

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    try:
        load_dotenv(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            load_dotenv(encoding='latin-1')
        except:
            load_dotenv(encoding='cp1252')
except Exception as e:
    print(f"⚠️  Advertencia: No se pudo cargar .env: {e}")

# Obtener variables de entorno
DB_HOST = os.getenv("NEON_DB_HOST") or os.getenv("DB_HOST")
DB_PORT = os.getenv("NEON_DB_PORT", "5432")
DB_NAME = os.getenv("NEON_DB_NAME") or os.getenv("DB_NAME")
DB_USER = os.getenv("NEON_DB_USER") or os.getenv("DB_USER")
DB_PASSWORD = os.getenv("NEON_DB_PASSWORD") or os.getenv("DB_PASSWORD")
DB_SSLMODE = os.getenv("NEON_DB_SSLMODE", "require")
DB_CHANNEL_BINDING = os.getenv("NEON_DB_CHANNEL_BINDING", "require")

# Construir URL de conexión
DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?sslmode={DB_SSLMODE}&channel_binding={DB_CHANNEL_BINDING}"
)

def run_migration():
    """Ejecuta la migración de índices"""
    print("=" * 60)
    print("🚀 EJECUTANDO MIGRACIÓN DE ÍNDICES DE RENDIMIENTO")
    print("=" * 60)
    
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        print("❌ Error: Faltan variables de entorno requeridas")
        sys.exit(1)
    
    migration_file = Path(__file__).parent / "migrations" / "add_performance_indexes.sql"
    
    if not migration_file.exists():
        print(f"❌ Archivo no encontrado: {migration_file}")
        sys.exit(1)
    
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
        
        print(f"\n📍 Conectando a base de datos...")
        print(f"   Host: {DB_HOST}")
        print(f"   Database: {DB_NAME}")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"   ✅ Conexión exitosa")
            print(f"   PostgreSQL: {version.split(',')[0]}")
        
        print(f"\n📄 Ejecutando: {migration_file.name}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with engine.connect() as conn:
            conn.execute(text(sql_content))
            conn.commit()
        
        print(f"✅ Migración completada exitosamente")
        print("\n💡 Los índices han sido creados para mejorar el rendimiento de consultas")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
