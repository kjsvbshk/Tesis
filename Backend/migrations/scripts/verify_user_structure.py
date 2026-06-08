#!/usr/bin/env python3
"""
Script de verificación de estructura de usuarios
Verifica que:
1. Todos los usuarios tengan registro en su tabla correspondiente
2. avatar_url no esté en user_accounts
3. Cada usuario tenga exactamente un registro en clients/administrators/operators
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
    load_dotenv()
except:
    pass

# Obtener variables de entorno
DB_HOST = os.getenv("NEON_DB_HOST") or os.getenv("DB_HOST")
DB_PORT = os.getenv("NEON_DB_PORT", "5432")
DB_NAME = os.getenv("NEON_DB_NAME") or os.getenv("DB_NAME")
DB_USER = os.getenv("NEON_DB_USER") or os.getenv("DB_USER")
DB_PASSWORD = os.getenv("NEON_DB_PASSWORD") or os.getenv("DB_PASSWORD")
DB_SSLMODE = os.getenv("NEON_DB_SSLMODE", "require")
DB_CHANNEL_BINDING = os.getenv("NEON_DB_CHANNEL_BINDING", "require")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?sslmode={DB_SSLMODE}&channel_binding={DB_CHANNEL_BINDING}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def main():
    """Ejecutar verificación completa"""
    print("=" * 80)
    print("🔍 VERIFICACIÓN DE ESTRUCTURA DE USUARIOS")
    print("=" * 80)
    print()
    
    issues = []
    warnings = []
    
    with engine.connect() as conn:
        # ========================================================================
        # 1. VERIFICAR QUE avatar_url NO ESTÁ EN user_accounts
        # ========================================================================
        print("1. VERIFICANDO QUE avatar_url NO ESTÁ EN user_accounts")
        print("-" * 80)
        
        query1 = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns
                WHERE table_schema = 'app'
                AND table_name = 'user_accounts'
                AND column_name = 'avatar_url'
            )
        """)
        has_avatar = conn.execute(query1).scalar()
        
        if has_avatar:
            print_error("avatar_url todavía existe en user_accounts")
            issues.append("avatar_url no eliminado de user_accounts")
        else:
            print_success("avatar_url no existe en user_accounts")
        
        print()
        
        # ========================================================================
        # 2. VERIFICAR QUE avatar_url EXISTE EN TABLAS INDIVIDUALES
        # ========================================================================
        print("2. VERIFICANDO QUE avatar_url EXISTE EN TABLAS INDIVIDUALES")
        print("-" * 80)
        
        tables_to_check = ['clients', 'administrators', 'operators']
        for table in tables_to_check:
            query = text(f"""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns
                    WHERE table_schema = 'app'
                    AND table_name = '{table}'
                    AND column_name = 'avatar_url'
                )
            """)
            has_col = conn.execute(query).scalar()
            if has_col:
                print_success(f"avatar_url existe en {table}")
            else:
                print_error(f"avatar_url NO existe en {table}")
                issues.append(f"avatar_url faltante en {table}")
        
        print()
        
        # ========================================================================
        # 3. VERIFICAR QUE TODOS LOS USUARIOS TIENEN REGISTRO EN SU TABLA
        # ========================================================================
        print("3. VERIFICANDO QUE TODOS LOS USUARIOS TIENEN REGISTRO EN SU TABLA")
        print("-" * 80)
        
        query3 = text("""
            SELECT ua.id, ua.username
            FROM app.user_accounts ua
            WHERE NOT EXISTS (
                SELECT 1 FROM app.clients WHERE user_account_id = ua.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM app.administrators WHERE user_account_id = ua.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM app.operators WHERE user_account_id = ua.id
            )
        """)
        orphaned_users = conn.execute(query3).fetchall()
        
        if orphaned_users:
            print_error(f"Hay {len(orphaned_users)} usuarios sin registro en ninguna tabla:")
            for user in orphaned_users[:10]:  # Mostrar máximo 10
                print(f"  - ID: {user[0]}, Username: {user[1]}")
            if len(orphaned_users) > 10:
                print(f"  ... y {len(orphaned_users) - 10} más")
            issues.append(f"{len(orphaned_users)} usuarios sin tabla")
        else:
            print_success("Todos los usuarios tienen registro en su tabla correspondiente")
        
        print()
        
        # ========================================================================
        # 4. VERIFICAR QUE CADA USUARIO TIENE EXACTAMENTE UN REGISTRO
        # ========================================================================
        print("4. VERIFICANDO QUE CADA USUARIO TIENE EXACTAMENTE UN REGISTRO")
        print("-" * 80)
        
        query4 = text("""
            SELECT ua.id, ua.username,
                (SELECT COUNT(*) FROM app.clients WHERE user_account_id = ua.id) as in_clients,
                (SELECT COUNT(*) FROM app.administrators WHERE user_account_id = ua.id) as in_admins,
                (SELECT COUNT(*) FROM app.operators WHERE user_account_id = ua.id) as in_operators
            FROM app.user_accounts ua
            WHERE (
                (SELECT COUNT(*) FROM app.clients WHERE user_account_id = ua.id) +
                (SELECT COUNT(*) FROM app.administrators WHERE user_account_id = ua.id) +
                (SELECT COUNT(*) FROM app.operators WHERE user_account_id = ua.id)
            ) > 1
        """)
        duplicate_users = conn.execute(query4).fetchall()
        
        if duplicate_users:
            print_error(f"Hay {len(duplicate_users)} usuarios con múltiples registros:")
            for user in duplicate_users[:10]:
                print(f"  - ID: {user[0]}, Username: {user[1]} (clients: {user[2]}, admins: {user[3]}, operators: {user[4]})")
            if len(duplicate_users) > 10:
                print(f"  ... y {len(duplicate_users) - 10} más")
            issues.append(f"{len(duplicate_users)} usuarios con múltiples registros")
        else:
            print_success("Cada usuario tiene exactamente un registro")
        
        print()
        
        # ========================================================================
        # 5. VERIFICAR MIGRACIÓN DE avatar_url
        # ========================================================================
        print("5. VERIFICANDO MIGRACIÓN DE avatar_url")
        print("-" * 80)
        
        # Contar usuarios con avatar_url en tablas individuales
        query5 = text("""
            SELECT 
                (SELECT COUNT(*) FROM app.clients WHERE avatar_url IS NOT NULL) as clients_with_avatar,
                (SELECT COUNT(*) FROM app.administrators WHERE avatar_url IS NOT NULL) as admins_with_avatar,
                (SELECT COUNT(*) FROM app.operators WHERE avatar_url IS NOT NULL) as operators_with_avatar
        """)
        result5 = conn.execute(query5).fetchone()
        if result5:
            clients_count = result5[0] or 0
            admins_count = result5[1] or 0
            operators_count = result5[2] or 0
            total = clients_count + admins_count + operators_count
            print_info(f"Usuarios con avatar_url: {total} (clients: {clients_count}, admins: {admins_count}, operators: {operators_count})")
        
        print()
        
        # ========================================================================
        # 6. RESUMEN
        # ========================================================================
        print("=" * 80)
        print("📊 RESUMEN DE VERIFICACIÓN")
        print("=" * 80)
        print()
        
        if not issues and not warnings:
            print_success("✅ TODAS LAS VERIFICACIONES PASARON")
            print("   La estructura de usuarios está correcta.")
        else:
            if issues:
                print_error(f"❌ PROBLEMAS ENCONTRADOS: {len(issues)}")
                for i, issue in enumerate(issues, 1):
                    print(f"   {i}. {issue}")
                print()
            
            if warnings:
                print_warning(f"⚠️  ADVERTENCIAS: {len(warnings)}")
                for i, warning in enumerate(warnings, 1):
                    print(f"   {i}. {warning}")
                print()
        
        print("=" * 80)
        
        # Exit code
        sys.exit(0 if not issues else 1)

if __name__ == "__main__":
    main()
