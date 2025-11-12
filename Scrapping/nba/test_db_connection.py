#!/usr/bin/env python3
"""
Script para probar la conexión a la base de datos usando .env
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Cargar variables de entorno desde .env
if os.path.exists('.env'):
    load_dotenv('.env')
    print("[OK] Archivo .env cargado")
else:
    load_dotenv()
    print("[WARN] No se encontro .env, usando variables de entorno del sistema")

# Construir DATABASE_URL desde variables individuales o usar la completa
database_url = os.getenv("DATABASE_URL")

# Si no hay DATABASE_URL completa, construir desde variables individuales
if not database_url:
    db_host = os.getenv("NEON_DB_HOST")
    db_port = os.getenv("NEON_DB_PORT", "5432")
    db_name = os.getenv("NEON_DB_NAME")
    db_user = os.getenv("NEON_DB_USER")
    db_password = os.getenv("NEON_DB_PASSWORD")
    sslmode = os.getenv("NEON_DB_SSLMODE", "require")
    channel_binding = os.getenv("NEON_DB_CHANNEL_BINDING", "require")
    
    print(f"\nVariables encontradas:")
    print(f"  NEON_DB_HOST: {db_host}")
    print(f"  NEON_DB_PORT: {db_port}")
    print(f"  NEON_DB_NAME: {db_name}")
    print(f"  NEON_DB_USER: {db_user}")
    print(f"  NEON_DB_PASSWORD: {'*' * len(db_password) if db_password else 'None'}")
    
    if all([db_host, db_port, db_name, db_user, db_password]):
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode={sslmode}&channel_binding={channel_binding}"
        print(f"\n[OK] DATABASE_URL construida desde variables individuales")
    else:
        print(f"\n[ERROR] Faltan variables requeridas para construir DATABASE_URL")
        sys.exit(1)
else:
    print(f"\n[OK] DATABASE_URL encontrada en variables de entorno")

# Ocultar password en la URL para mostrar
safe_url = database_url.split('@')[0].split(':')[-1] + '@' + '@'.join(database_url.split('@')[1:])
print(f"  URL: postgresql://***@{safe_url.split('@')[1]}")

# Probar conexión
print(f"\n{'='*60}")
print("Probando conexión a la base de datos...")
print(f"{'='*60}")

try:
    engine = create_engine(database_url, pool_pre_ping=True)
    
    with engine.connect() as conn:
        # Probar query simple
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"[OK] Conexion exitosa!")
        print(f"  PostgreSQL version: {version.split(',')[0]}")
        
        # Verificar esquema
        schema = os.getenv("DB_SCHEMA", "espn")
        result = conn.execute(text(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{schema}'"))
        schema_exists = result.fetchone()
        
        if schema_exists:
            print(f"[OK] Esquema '{schema}' existe")
        else:
            print(f"[WARN] Esquema '{schema}' no existe (se creara cuando sea necesario)")
        
        # Listar tablas en el esquema
        result = conn.execute(text(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{schema}'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            print(f"\n[OK] Tablas encontradas en esquema '{schema}': {len(tables)}")
            for table in tables[:10]:  # Mostrar solo las primeras 10
                print(f"  - {table}")
            if len(tables) > 10:
                print(f"  ... y {len(tables) - 10} mas")
        else:
            print(f"\n[WARN] No hay tablas en el esquema '{schema}'")
    
    print(f"\n{'='*60}")
    print("[OK] Prueba de conexion completada exitosamente")
    print(f"{'='*60}")
    
except Exception as e:
    print(f"\n[ERROR] Error de conexion: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

