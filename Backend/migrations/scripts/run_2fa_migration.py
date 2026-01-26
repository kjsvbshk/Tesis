"""
Script para ejecutar la migración de 2FA y Sesiones
Ejecuta el script SQL de migración para crear las tablas de 2FA y sesiones
"""

import sys
import os
from sqlalchemy import text

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from app.core.database import sys_engine
from app.core.config import settings

def run_migration():
    """Ejecutar migración SQL"""
    print("=" * 60)
    print("🚀 MIGRACIÓN: 2FA y Sesiones")
    print("=" * 60)
    
    migration_file = os.path.join(os.path.dirname(__file__), '..', 'add_2fa_avatar_sessions.sql')
    
    if not os.path.exists(migration_file):
        print(f"❌ Error: No se encontró el archivo de migración: {migration_file}")
        sys.exit(1)
    
    try:
        print(f"\n📄 Leyendo archivo de migración: {migration_file}")
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("\n🔧 Ejecutando migración SQL...")
        with sys_engine.connect() as conn:
            # Ejecutar el script SQL
            conn.execute(text(sql_script))
            conn.commit()
        
        print("   ✅ Migración ejecutada exitosamente")
        
        # Verificar resultados
        print("\n🔍 Verificando cambios...")
        with sys_engine.connect() as conn:
            # Verificar tablas
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'app' 
                    AND table_name = 'user_two_factor'
                ) as exists
            """))
            two_factor_exists = result.scalar()
            
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'app' 
                    AND table_name = 'user_sessions'
                ) as exists
            """))
            sessions_exists = result.scalar()
            
            print("\n📋 Resultados:")
            print(f"   user_two_factor: {'✅ Existe' if two_factor_exists else '❌ No existe'}")
            print(f"   user_sessions: {'✅ Existe' if sessions_exists else '❌ No existe'}")
            
            if two_factor_exists and sessions_exists:
                print("\n" + "=" * 60)
                print("✅ Migración completada exitosamente")
                print("=" * 60)
            else:
                print("\n⚠️  Algunos elementos no se crearon correctamente")
        
    except Exception as e:
        print(f"\n❌ Error ejecutando migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
