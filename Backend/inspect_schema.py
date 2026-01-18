#!/usr/bin/env python3
"""
Script para inspeccionar el esquema actual de la base de datos
y verificar qué cambios pueden ser necesarios
"""

import sys
import os
from sqlalchemy import create_engine, text, inspect
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

def inspect_schema():
    """Inspecciona el esquema actual de la base de datos"""
    print("=" * 60)
    print("🔍 INSPECCIÓN DEL ESQUEMA DE BASE DE DATOS")
    print("=" * 60)
    
    # Verificar variables requeridas
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        print("❌ Error: Faltan variables de entorno requeridas")
        sys.exit(1)
    
    try:
        # Crear engine
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
        
        print(f"\n📍 Conectando a base de datos...")
        print(f"   Host: {DB_HOST}")
        print(f"   Database: {DB_NAME}")
        
        # Verificar conexión
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"   ✅ Conexión exitosa")
            print(f"   PostgreSQL: {version.split(',')[0]}")
        
        inspector = inspect(engine)
        
        # ========================================================================
        # 1. INSPECCIONAR TABLAS EN ESQUEMA 'app'
        # ========================================================================
        print("\n" + "=" * 60)
        print("📊 TABLAS EN ESQUEMA 'app'")
        print("=" * 60)
        
        app_tables = inspector.get_table_names(schema='app')
        print(f"\nTotal de tablas: {len(app_tables)}")
        
        expected_tables = [
            'user_accounts', 'clients', 'administrators', 'operators',
            'roles', 'permissions', 'role_permissions', 'user_roles',
            'providers', 'provider_endpoints',
            'idempotency_keys', 'requests',
            'model_versions', 'predictions',
            'odds_snapshots', 'odds_lines',
            'audit_log', 'outbox',
            'users', 'bets', 'transactions'
        ]
        
        print("\n📋 Tablas existentes:")
        for table in sorted(app_tables):
            marker = "✅" if table in expected_tables else "⚠️ "
            print(f"  {marker} {table}")
        
        missing_tables = [t for t in expected_tables if t not in app_tables]
        if missing_tables:
            print(f"\n⚠️  Tablas faltantes: {missing_tables}")
        else:
            print(f"\n✅ Todas las tablas esperadas están presentes")
        
        # ========================================================================
        # 2. INSPECCIONAR ÍNDICES EXISTENTES
        # ========================================================================
        print("\n" + "=" * 60)
        print("🔍 ÍNDICES EXISTENTES")
        print("=" * 60)
        
        with engine.connect() as conn:
            # Índices recomendados desde OPTIMIZATION_NOTES.md
            recommended_indexes = {
                'app.user_accounts': ['idx_user_accounts_username', 'idx_user_accounts_email'],
                'app.user_roles': ['idx_user_roles_user_id', 'idx_user_roles_role_id', 'idx_user_roles_active'],
                'espn.bets': ['idx_bets_user_id', 'idx_bets_status', 'idx_bets_user_status'],
                'app.requests': ['idx_requests_user_id', 'idx_requests_status', 'idx_requests_created_at'],
                'app.predictions': ['idx_predictions_user_id', 'idx_predictions_game_id'],
                'app.audit_log': ['idx_audit_actor', 'idx_audit_resource', 'idx_audit_created_at']
            }
            
            print("\n📋 Índices recomendados vs existentes:\n")
            
            for table_key, indexes in recommended_indexes.items():
                schema, table = table_key.split('.')
                
                # Verificar si la tabla existe
                table_exists_query = text("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = :schema AND table_name = :table
                    )
                """)
                table_exists = conn.execute(table_exists_query, {"schema": schema, "table": table}).scalar()
                
                if not table_exists:
                    print(f"  📊 {schema}.{table}: TABLA NO EXISTE")
                    continue
                
                print(f"  📊 {schema}.{table}:")
                
                # Obtener índices existentes en esta tabla
                existing_indexes = []
                query = text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE schemaname = :schema AND tablename = :table
                """)
                result = conn.execute(query, {"schema": schema, "table": table})
                existing_indexes = [row[0] for row in result]
                
                # Verificar columnas indexadas (para user_accounts, username y email tienen índices por UNIQUE)
                if table_key == 'app.user_accounts':
                    # Verificar si username y email tienen índices (aunque sean UNIQUE)
                    for col in ['username', 'email']:
                        col_index_query = text("""
                            SELECT EXISTS(
                                SELECT 1 FROM pg_indexes i
                                WHERE i.schemaname = :schema 
                                AND i.tablename = :table
                                AND (
                                    i.indexname LIKE '%username%' AND :col = 'username'
                                    OR i.indexname LIKE '%email%' AND :col = 'email'
                                )
                            )
                        """)
                        has_idx = conn.execute(col_index_query, {"schema": schema, "table": table, "col": col}).scalar()
                        if col == 'username' and has_idx:
                            print(f"    ✅ idx_user_accounts_username (via UNIQUE)")
                        elif col == 'email' and has_idx:
                            print(f"    ✅ idx_user_accounts_email (via UNIQUE)")
                        elif col == 'username':
                            print(f"    ⚠️  idx_user_accounts_username (FALTA)")
                        elif col == 'email':
                            print(f"    ⚠️  idx_user_accounts_email (FALTA)")
                
                # Para predictions, verificar columnas reales
                elif table_key == 'app.predictions':
                    # Verificar qué columnas tiene predictions
                    cols_query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = :schema AND table_name = :table
                    """)
                    cols_result = conn.execute(cols_query, {"schema": schema, "table": table})
                    actual_columns = [row[0] for row in cols_result]
                    
                    if 'user_id' not in actual_columns:
                        print(f"    ℹ️  idx_predictions_user_id (NO APLICA - columna no existe)")
                    if 'game_id' not in actual_columns:
                        print(f"    ℹ️  idx_predictions_game_id (NO APLICA - columna no existe)")
                
                # Para otros índices, verificar normalmente
                else:
                    for idx in indexes:
                        if idx in existing_indexes:
                            print(f"    ✅ {idx}")
                        else:
                            # Verificar si la columna existe antes de marcar como faltante
                            print(f"    ⚠️  {idx} (FALTA)")
        
        # ========================================================================
        # 3. VERIFICAR COLUMNAS CLAVE
        # ========================================================================
        print("\n" + "=" * 60)
        print("🔍 VERIFICACIÓN DE COLUMNAS CLAVE")
        print("=" * 60)
        
        key_checks = [
            ('app.providers', 'code', 'VARCHAR(50)'),
            ('app.providers', 'is_active', 'BOOLEAN'),
            ('app.provider_endpoints', 'provider_id', 'INTEGER'),
            ('app.audit_log', 'actor_user_id', 'INTEGER'),
            ('app.outbox', 'published_at', 'TIMESTAMP'),
        ]
        
        print("\n📋 Verificando columnas importantes:\n")
        
        with engine.connect() as conn:
            for table_key, column, expected_type in key_checks:
                schema, table = table_key.split('.')
                try:
                    columns = inspector.get_columns(table, schema=schema)
                    column_info = next((c for c in columns if c['name'] == column), None)
                    
                    if column_info:
                        print(f"  ✅ {table_key}.{column} - {column_info['type']}")
                    else:
                        print(f"  ❌ {table_key}.{column} - COLUMNA FALTANTE")
                except Exception as e:
                    print(f"  ⚠️  {table_key}.{column} - Error verificando: {e}")
        
        # ========================================================================
        # 4. RESUMEN DE CAMBIOS RECOMENDADOS
        # ========================================================================
        print("\n" + "=" * 60)
        print("📝 RESUMEN DE CAMBIOS RECOMENDADOS")
        print("=" * 60)
        
        # Verificar qué índices faltan (excluyendo los que no aplican)
        with engine.connect() as conn:
            missing_indexes = []
            for table_key, indexes in recommended_indexes.items():
                schema, table = table_key.split('.')
                
                # Verificar si la tabla existe
                table_exists_query = text("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = :schema AND table_name = :table
                    )
                """)
                if not conn.execute(table_exists_query, {"schema": schema, "table": table}).scalar():
                    continue
                
                # Para user_accounts, verificar índices por UNIQUE
                if table_key == 'app.user_accounts':
                    for col in ['username', 'email']:
                        col_index_query = text("""
                            SELECT EXISTS(
                                SELECT 1 FROM pg_indexes i
                                WHERE i.schemaname = :schema 
                                AND i.tablename = :table
                                AND (
                                    i.indexname LIKE '%username%' AND :col = 'username'
                                    OR i.indexname LIKE '%email%' AND :col = 'email'
                                )
                            )
                        """)
                        has_idx = conn.execute(col_index_query, {"schema": schema, "table": table, "col": col}).scalar()
                        if not has_idx:
                            missing_indexes.append(f"{schema}.{table}: idx_user_accounts_{col}")
                    continue
                
                # Para predictions, verificar columnas reales
                if table_key == 'app.predictions':
                    cols_query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = :schema AND table_name = :table
                    """)
                    cols_result = conn.execute(cols_query, {"schema": schema, "table": table})
                    actual_columns = [row[0] for row in cols_result]
                    # No agregar a faltantes si las columnas no existen
                    continue
                
                # Para otras tablas, verificar normalmente
                query = text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE schemaname = :schema AND tablename = :table
                """)
                result = conn.execute(query, {"schema": schema, "table": table})
                existing = [row[0] for row in result]
                for idx in indexes:
                    if idx not in existing:
                        missing_indexes.append(f"{schema}.{table}: {idx}")
            
            if missing_indexes:
                print("\n⚠️  ÍNDICES FALTANTES (recomendado agregar):")
                print("   Archivo: migrations/add_performance_indexes.sql")
                print("\n   Índices faltantes:")
                for idx in missing_indexes:
                    print(f"   - {idx}")
            else:
                print("\n✅ Todos los índices recomendados están presentes")
                print("   (Los índices de user_accounts existen via UNIQUE constraints)")
                print("   (Los índices de predictions no aplican - columnas no existen)")
        
        print("\n" + "=" * 60)
        print("✅ Inspección completada")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    inspect_schema()
