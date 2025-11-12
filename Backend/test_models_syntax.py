"""
Script de prueba para verificar sintaxis de modelos sin conexión a BD
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
print("🧪 PRUEBA DE SINTAXIS DE MODELOS")
print("=" * 60)

errors = []

try:
    print("\n1️⃣  Verificando importaciones...")
    from app.models import (
        Role, Permission, RolePermission, UserRole,
        IdempotencyKey, Request, RequestStatus,
        ModelVersion, Prediction,
        Provider, ProviderEndpoint,
        OddsSnapshot, OddsLine,
        AuditLog, Outbox,
        User, Bet, Transaction
    )
    print("   ✅ Todas las importaciones exitosas")
    
    print("\n2️⃣  Verificando estructura de modelos...")
    from app.core.database import SysBase
    
    # Verificar que los modelos tengan __tablename__
    models_to_check = [
        (Role, "Role"),
        (Permission, "Permission"),
        (RolePermission, "RolePermission"),
        (UserRole, "UserRole"),
        (IdempotencyKey, "IdempotencyKey"),
        (Request, "Request"),
        (ModelVersion, "ModelVersion"),
        (Prediction, "Prediction"),
        (Provider, "Provider"),
        (ProviderEndpoint, "ProviderEndpoint"),
        (OddsSnapshot, "OddsSnapshot"),
        (OddsLine, "OddsLine"),
        (AuditLog, "AuditLog"),
        (Outbox, "Outbox"),
    ]
    
    for model, name in models_to_check:
        if not hasattr(model, '__tablename__'):
            errors.append(f"❌ {name} no tiene __tablename__")
        else:
            print(f"   ✅ {name} tiene __tablename__ = '{model.__tablename__}'")
    
    print("\n3️⃣  Verificando relaciones...")
    # Verificar relaciones
    if hasattr(User, 'roles'):
        print("   ✅ User.roles definida")
    else:
        errors.append("❌ User.roles no definida")
    
    if hasattr(Role, 'permissions'):
        print("   ✅ Role.permissions definida")
    else:
        errors.append("❌ Role.permissions no definida")
    
    if hasattr(Role, 'users'):
        print("   ✅ Role.users definida")
    else:
        errors.append("❌ Role.users no definida")
    
    if hasattr(Request, 'user'):
        print("   ✅ Request.user definida")
    else:
        errors.append("❌ Request.user no definida")
    
    if hasattr(Prediction, 'request'):
        print("   ✅ Prediction.request definida")
    else:
        errors.append("❌ Prediction.request no definida")
    
    if hasattr(Prediction, 'model_version'):
        print("   ✅ Prediction.model_version definida")
    else:
        errors.append("❌ Prediction.model_version no definida")
    
    if hasattr(Provider, 'endpoints'):
        print("   ✅ Provider.endpoints definida")
    else:
        errors.append("❌ Provider.endpoints no definida")
    
    if hasattr(OddsSnapshot, 'odds_lines'):
        print("   ✅ OddsSnapshot.odds_lines definida")
    else:
        errors.append("❌ OddsSnapshot.odds_lines no definida")
    
    print("\n4️⃣  Verificando que las tablas estén registradas...")
    tables = SysBase.metadata.tables
    expected_tables = [
        'app.roles', 'app.permissions', 'app.role_permissions', 'app.user_roles',
        'app.idempotency_keys', 'app.requests',
        'app.model_versions', 'app.predictions',
        'app.providers', 'app.provider_endpoints',
        'app.odds_snapshots', 'app.odds_lines',
        'app.audit_log', 'app.outbox',
    ]
    
    for table_name in expected_tables:
        if table_name in tables:
            print(f"   ✅ Tabla '{table_name}' registrada")
        else:
            errors.append(f"❌ Tabla '{table_name}' no registrada")
    
    print("\n5️⃣  Verificando que no haya nombres reservados...")
    # Verificar que no se use 'metadata' como nombre de columna
    reserved_names = ['metadata']
    for model, name in models_to_check:
        if hasattr(model, '__table__'):
            for column in model.__table__.columns:
                if column.name in reserved_names:
                    errors.append(f"❌ {name} tiene columna '{column.name}' que es reservado")
    
    print("   ✅ No se encontraron nombres reservados")
    
    print("\n" + "=" * 60)
    if errors:
        print("❌ SE ENCONTRARON ERRORES:")
        for error in errors:
            print(f"   {error}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("✅ TODOS LOS MODELOS ESTÁN CORRECTAMENTE DEFINIDOS")
        print("=" * 60)
        print(f"\n📊 Total de tablas registradas: {len(tables)}")
        print("\n✅ La sintaxis de los modelos es correcta")
        print("   (Nota: Esto no prueba la conexión a BD, solo la sintaxis)")
    
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

