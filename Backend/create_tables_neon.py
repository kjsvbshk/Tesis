"""
Script para crear las tablas en Neon
Ejecutar una vez para crear todas las tablas del esquema app
"""

import sys
import os
from sqlalchemy import create_engine, text, inspect

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Usar settings de la aplicación que ya maneja las variables de Neon
from app.core.config import settings
from app.core.database import sys_engine, SysBase, EspnBase

# Usar las variables de settings que ya apuntan a Neon
DB_HOST = settings.DB_HOST
DB_PORT = settings.DB_PORT
DB_NAME = settings.DB_NAME
DB_USER = settings.DB_USER
DB_PASSWORD = settings.DB_PASSWORD
DB_SCHEMA = settings.DB_SCHEMA

# Importar todos los modelos para que SQLAlchemy los registre
from app.models import (
    # Core models
    user, bet, transaction,
    team, game, team_stats,
    # RBAC models
    Role, Permission, RolePermission, UserRole,
    # Idempotency and requests
    IdempotencyKey, Request,
    # Predictions
    ModelVersion, Prediction,
    # Providers
    Provider, ProviderEndpoint,
    # Snapshots
    OddsSnapshot, OddsLine,
    # Audit and messaging
    AuditLog, Outbox,
)

def create_tables():
    """Crear todas las tablas en Neon"""
    print("=" * 60)
    print("🚀 CREACIÓN DE TABLAS EN NEON")
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
    
    try:
        # Verificar conexión a Neon
        print(f"\n📍 Conectando a Neon...")
        print(f"   Host: {DB_HOST}")
        print(f"   Database: {DB_NAME}")
        print(f"   Schema: {DB_SCHEMA}")
        
        # Crear esquema si no existe
        with sys_engine.connect() as conn:
            # Crear esquema app si no existe
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
            conn.commit()
            print(f"   ✅ Esquema '{DB_SCHEMA}' verificado/creado")
        
        print("\n📊 Creando tablas del esquema app...")
        # Crear tablas de app
        SysBase.metadata.create_all(bind=sys_engine)
        print("   ✅ Tablas del esquema app creadas")
        
        # Verificar tablas creadas
        print("\n🔍 Verificando tablas creadas...")
        with sys_engine.connect() as conn:
            inspector = inspect(sys_engine)
            existing_tables = inspector.get_table_names(schema=DB_SCHEMA)
            
            expected_tables = [
                'roles', 'permissions', 'role_permissions', 'user_roles',
                'idempotency_keys', 'requests',
                'model_versions', 'predictions',
                'providers', 'provider_endpoints',
                'odds_snapshots', 'odds_lines',
                'audit_log', 'outbox',
                'users', 'bets', 'transactions'
            ]
            
            print(f"\n📋 Tablas en esquema '{DB_SCHEMA}':")
            for table in sorted(existing_tables):
                if table in expected_tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ⚠️  {table} (no esperada)")
            
            missing = [t for t in expected_tables if t not in existing_tables]
            if missing:
                print(f"\n⚠️  Tablas faltantes: {missing}")
            else:
                print(f"\n✅ Todas las tablas esperadas están creadas ({len(existing_tables)}/{len(expected_tables)})")
        
        print("\n" + "=" * 60)
        print("✅ Proceso completado")
        print("=" * 60)
        print("\n💡 Próximo paso: Ejecutar 'python init_rbac_data.py' para inicializar roles y permisos")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()

