"""
Script para verificar que la migración se aplicó correctamente
"""

import sys
from sqlalchemy import inspect

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from app.core.database import sys_engine

def verify_migration():
    """Verificar estructura de tablas"""
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE MIGRACIÓN")
    print("=" * 60)
    
    inspector = inspect(sys_engine)
    
    # Verificar user_accounts
    print("\n1. Tabla: user_accounts")
    try:
        cols = inspector.get_columns('user_accounts', schema='app')
        print(f"   ✅ Tabla existe ({len(cols)} columnas)")
        avatar_col = [c for c in cols if c['name'] == 'avatar_url']
        if avatar_col:
            print(f"   ✅ Campo avatar_url existe: {avatar_col[0]['type']}")
        else:
            print("   ❌ Campo avatar_url NO existe")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Verificar user_two_factor
    print("\n2. Tabla: user_two_factor")
    try:
        cols = inspector.get_columns('user_two_factor', schema='app')
        print(f"   ✅ Tabla existe ({len(cols)} columnas)")
        print("   Columnas:")
        for col in cols:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"      - {col['name']}: {col['type']} {nullable}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Verificar user_sessions
    print("\n3. Tabla: user_sessions")
    try:
        cols = inspector.get_columns('user_sessions', schema='app')
        print(f"   ✅ Tabla existe ({len(cols)} columnas)")
        print("   Columnas principales:")
        key_cols = ['id', 'user_account_id', 'token_hash', 'is_active', 'expires_at']
        for col in cols:
            if col['name'] in key_cols:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                print(f"      - {col['name']}: {col['type']} {nullable}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Verificar índices
    print("\n4. Índices:")
    try:
        indexes = inspector.get_indexes('user_two_factor', schema='app')
        print("   user_two_factor:")
        for idx in indexes:
            print(f"      - {idx['name']}: {', '.join(idx['column_names'])}")
        
        indexes = inspector.get_indexes('user_sessions', schema='app')
        print("   user_sessions:")
        for idx in indexes:
            print(f"      - {idx['name']}: {', '.join(idx['column_names'])}")
    except Exception as e:
        print(f"   ⚠️  Error verificando índices: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Verificación completada")
    print("=" * 60)

if __name__ == "__main__":
    verify_migration()
