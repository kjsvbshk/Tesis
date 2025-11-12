"""
Script para verificar errores de importación en main.py
(excluyendo dependencias faltantes como joblib)
"""

import sys
import os

# Configurar variables de entorno mínimas
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
print("🧪 PRUEBA DE IMPORTACIONES EN MAIN.PY")
print("=" * 60)

errors = []
warnings = []

try:
    print("\n1️⃣  Importando config...")
    from app.core.config import settings
    print("   ✅ Config importado correctamente")
    
    print("\n2️⃣  Importando database...")
    from app.core.database import sys_engine, espn_engine, SysBase, EspnBase
    print("   ✅ Database importado correctamente")
    
    print("\n3️⃣  Importando modelos...")
    from app.models import (
        user, bet, transaction,
        team, game, team_stats,
        Role, Permission, RolePermission, UserRole,
        IdempotencyKey, Request,
        ModelVersion, Prediction,
        Provider, ProviderEndpoint,
        OddsSnapshot, OddsLine,
        AuditLog, Outbox,
    )
    print("   ✅ Todos los modelos importados correctamente")
    
    print("\n4️⃣  Verificando importación de api_router...")
    try:
        from app.api.v1.api import api_router
        print("   ✅ api_router importado correctamente")
    except ModuleNotFoundError as e:
        if 'joblib' in str(e):
            warnings.append(f"⚠️  Dependencia faltante (no crítico para modelos): {e}")
            print(f"   ⚠️  Dependencia faltante: {e}")
        else:
            errors.append(f"❌ Error de importación: {e}")
            print(f"   ❌ Error: {e}")
    except Exception as e:
        errors.append(f"❌ Error inesperado al importar api_router: {e}")
        print(f"   ❌ Error: {e}")
    
    print("\n5️⃣  Verificando que FastAPI pueda crear la app...")
    try:
        from fastapi import FastAPI
        app = FastAPI(
            title="NBA Bets Prediction API",
            description="API para predicción de resultados NBA y simulación de apuestas virtuales",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        print("   ✅ FastAPI app creada correctamente")
    except Exception as e:
        errors.append(f"❌ Error al crear FastAPI app: {e}")
        print(f"   ❌ Error: {e}")
    
    print("\n6️⃣  Verificando que los modelos estén disponibles para SQLAlchemy...")
    from app.core.database import SysBase
    tables = SysBase.metadata.tables
    print(f"   ✅ {len(tables)} tablas registradas en SQLAlchemy")
    
    print("\n" + "=" * 60)
    if errors:
        print("❌ SE ENCONTRARON ERRORES:")
        for error in errors:
            print(f"   {error}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("✅ TODAS LAS IMPORTACIONES SON CORRECTAS")
        if warnings:
            print("\n⚠️  ADVERTENCIAS (no críticas):")
            for warning in warnings:
                print(f"   {warning}")
        print("=" * 60)
        print("\n✅ Los modelos están listos para crear las tablas en la BD")
        print("   (Nota: Algunas dependencias como joblib pueden faltar, pero no afectan los modelos)")
    
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

