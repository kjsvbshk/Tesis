#!/usr/bin/env python3
"""
Script para ejecutar migraciones SQL en orden
Ejecuta las migraciones de normalización del esquema
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
    print("   Usando variables de entorno del sistema...")

# Obtener variables de entorno directamente
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

# Crear engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

def run_migration_sql_file(file_path: Path):
    """Ejecuta un archivo SQL de migración"""
    print(f"\n{'='*60}")
    print(f"📄 Ejecutando: {file_path.name}")
    print(f"{'='*60}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with engine.connect() as conn:
            # Ejecutar el SQL completo
            conn.execute(text(sql_content))
            conn.commit()
        
        print(f"✅ Migración {file_path.name} completada exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error ejecutando {file_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar migraciones en orden"""
    print("=" * 60)
    print("🚀 EJECUTANDO MIGRACIONES DE NORMALIZACIÓN")
    print("=" * 60)
    
    # Verificar variables requeridas
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        print("❌ Error: Faltan variables de entorno requeridas:")
        if not DB_HOST: print("   - DB_HOST (o NEON_DB_HOST)")
        if not DB_NAME: print("   - DB_NAME (o NEON_DB_NAME)")
        if not DB_USER: print("   - DB_USER (o NEON_DB_USER)")
        if not DB_PASSWORD: print("   - DB_PASSWORD (o NEON_DB_PASSWORD)")
        print("\n💡 Asegúrate de configurar estas variables en tu archivo .env")
        sys.exit(1)
    
    # Obtener ruta del directorio de migraciones
    migrations_dir = Path(__file__).parent.parent
    
    # Definir orden de migraciones
    migration_files = [
        "normalize_espn_schema_3nf.sql",  # Primero: normalización de bets
        "normalize_users_by_type.sql",    # Segundo: separación de usuarios
    ]
    
    print(f"\n📍 Conectando a base de datos...")
    print(f"   Host: {DB_HOST}")
    print(f"   Database: {DB_NAME}")
    
    # Verificar conexión
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"   ✅ Conexión exitosa")
            print(f"   PostgreSQL: {version.split(',')[0]}")
    except Exception as e:
        print(f"   ❌ Error conectando: {e}")
        sys.exit(1)
    
    # Ejecutar migraciones en orden
    success_count = 0
    for migration_file in migration_files:
        file_path = migrations_dir / migration_file
        if not file_path.exists():
            print(f"\n⚠️  Archivo no encontrado: {file_path}")
            print(f"   Saltando migración...")
            continue
        
        if run_migration_sql_file(file_path):
            success_count += 1
        else:
            print(f"\n❌ Migración falló. Deteniendo ejecución.")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"✅ Migraciones completadas: {success_count}/{len(migration_files)}")
    print(f"{'='*60}")
    print("\n💡 Próximos pasos:")
    print("   1. Actualizar servicios y endpoints para usar los nuevos modelos")
    print("   2. Actualizar autenticación para usar UserAccount")
    print("   3. Verificar que todo funciona correctamente")

if __name__ == "__main__":
    main()

