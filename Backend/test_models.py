"""
Script de prueba para verificar que todos los modelos se importan correctamente
"""

import sys
import os

# Configurar variables de entorno mínimas antes de importar
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_SCHEMA", "app")
os.environ.setdefault("NBA_DB_HOST", "localhost")
os.environ.setdefault("NBA_DB_PORT", "5432")
os.environ.setdefault("NBA_DB_NAME", "test")
os.environ.setdefault("NBA_DB_USER", "test")
os.environ.setdefault("NBA_DB_PASSWORD", "test")
os.environ.setdefault("NBA_DB_SCHEMA", "espn")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

print("=" * 60)
print("🧪 PRUEBA DE IMPORTACIÓN DE MODELOS")
print("=" * 60)

try:
    print("\n1️⃣  Importando modelos RBAC...")
    from app.models import Role, Permission, RolePermission, UserRole
    print("   ✅ Role, Permission, RolePermission, UserRole")
    
    print("\n2️⃣  Importando modelos de idempotencia y requests...")
    from app.models import IdempotencyKey, Request, RequestStatus
    print("   ✅ IdempotencyKey, Request, RequestStatus")
    
    print("\n3️⃣  Importando modelos de predicciones...")
    from app.models import ModelVersion, Prediction
    print("   ✅ ModelVersion, Prediction")
    
    print("\n4️⃣  Importando modelos de proveedores...")
    from app.models import Provider, ProviderEndpoint
    print("   ✅ Provider, ProviderEndpoint")
    
    print("\n5️⃣  Importando modelos de snapshots...")
    from app.models import OddsSnapshot, OddsLine
    print("   ✅ OddsSnapshot, OddsLine")
    
    print("\n6️⃣  Importando modelos de auditoría y mensajería...")
    from app.models import AuditLog, Outbox
    print("   ✅ AuditLog, Outbox")
    
    print("\n7️⃣  Importando modelos core...")
    from app.models import User, Bet, Transaction
    print("   ✅ User, Bet, Transaction")
    
    print("\n8️⃣  Verificando relaciones...")
    # Verificar que las relaciones estén definidas
    assert hasattr(User, 'roles'), "User debe tener relación 'roles'"
    assert hasattr(Role, 'permissions'), "Role debe tener relación 'permissions'"
    assert hasattr(Role, 'users'), "Role debe tener relación 'users'"
    assert hasattr(Permission, 'roles'), "Permission debe tener relación 'roles'"
    assert hasattr(Request, 'user'), "Request debe tener relación 'user'"
    assert hasattr(Prediction, 'request'), "Prediction debe tener relación 'request'"
    assert hasattr(Prediction, 'model_version'), "Prediction debe tener relación 'model_version'"
    assert hasattr(Provider, 'endpoints'), "Provider debe tener relación 'endpoints'"
    assert hasattr(OddsSnapshot, 'odds_lines'), "OddsSnapshot debe tener relación 'odds_lines'"
    print("   ✅ Todas las relaciones están definidas correctamente")
    
    print("\n9️⃣  Verificando estructura de tablas...")
    from app.core.database import SysBase
    # Verificar que las tablas estén registradas
    tables = [table.name for table in SysBase.metadata.tables.values()]
    expected_tables = [
        'roles', 'permissions', 'role_permissions', 'user_roles',
        'idempotency_keys', 'requests',
        'model_versions', 'predictions',
        'providers', 'provider_endpoints',
        'odds_snapshots', 'odds_lines',
        'audit_log', 'outbox',
        'users', 'bets', 'transactions'
    ]
    
    for table in expected_tables:
        full_table_name = f"app.{table}"
        if full_table_name in SysBase.metadata.tables:
            print(f"   ✅ Tabla '{table}' registrada")
        else:
            print(f"   ⚠️  Tabla '{table}' no encontrada")
    
    print("\n" + "=" * 60)
    print("✅ TODOS LOS MODELOS SE IMPORTARON CORRECTAMENTE")
    print("=" * 60)
    print(f"\n📊 Total de tablas registradas: {len(SysBase.metadata.tables)}")
    
except ImportError as e:
    print(f"\n❌ Error de importación: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

