#!/usr/bin/env python3
"""
Script simplificado - Conexión a Neon PostgreSQL
"""

import sys
import os
from sqlalchemy import create_engine, text

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    # Intentar cargar con diferentes codificaciones
    try:
        load_dotenv(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            load_dotenv(encoding='latin-1')
        except:
            load_dotenv(encoding='cp1252')
except Exception as e:
    print(f"⚠️  Advertencia: No se pudo cargar .env: {e}")
    print("   Usando variables de entorno del sistema...")

# Conexión a Neon usando variables de entorno
NEON_DB_HOST = os.getenv("NEON_DB_HOST")
NEON_DB_PORT = os.getenv("NEON_DB_PORT", "5432")
NEON_DB_NAME = os.getenv("NEON_DB_NAME")
NEON_DB_USER = os.getenv("NEON_DB_USER")
NEON_DB_PASSWORD = os.getenv("NEON_DB_PASSWORD")
NEON_DB_SSLMODE = os.getenv("NEON_DB_SSLMODE", "require")
NEON_DB_CHANNEL_BINDING = os.getenv("NEON_DB_CHANNEL_BINDING", "require")

# Construir URL de conexión
NEON_DATABASE_URL = (
    f"postgresql://{NEON_DB_USER}:{NEON_DB_PASSWORD}@"
    f"{NEON_DB_HOST}:{NEON_DB_PORT}/{NEON_DB_NAME}"
    f"?sslmode={NEON_DB_SSLMODE}&channel_binding={NEON_DB_CHANNEL_BINDING}"
)

# Crear engine de conexión
neon_engine = create_engine(
    NEON_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

def test_connection():
    """Prueba la conexión a Neon"""
    print("=" * 60)
    print("🔍 PRUEBA DE CONEXIÓN A NEON")
    print("=" * 60)
    
    try:
        with neon_engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"\n✅ Conexión exitosa a Neon")
            print(f"📍 Host: {NEON_DB_HOST}")
            print(f"📊 Base de datos: {NEON_DB_NAME}")
            print(f"👤 Usuario: {NEON_DB_USER}")
            print(f"\n📝 Versión de PostgreSQL:")
            print(f"   {version}")
            
            # Verificar esquemas disponibles
            print(f"\n📦 Esquemas disponibles:")
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name
            """))
            schemas = [row[0] for row in result.fetchall()]
            for schema in schemas:
                print(f"   - {schema}")
            
            return True
    except Exception as e:
        print(f"\n❌ Error conectando a Neon: {e}")
        return False

if __name__ == "__main__":
    # Verificar que todas las variables estén configuradas
    required_vars = ["NEON_DB_HOST", "NEON_DB_NAME", "NEON_DB_USER", "NEON_DB_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Error: Faltan variables de entorno requeridas:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Asegúrate de configurar estas variables en tu archivo .env")
        sys.exit(1)
    
    success = test_connection()
    sys.exit(0 if success else 1)
