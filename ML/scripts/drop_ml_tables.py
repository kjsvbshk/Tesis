#!/usr/bin/env python3
"""
Script para eliminar todas las tablas del esquema ML
Deja el esquema limpio para definir nuevas tablas
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config


def drop_ml_tables():
    """
    Elimina todas las tablas del esquema ML
    """
    # Obtener URL de conexión (solo Neon)
    database_url = db_config.get_database_url()
    schema_name = db_config.get_schema("ml")
    
    print("=" * 60)
    print(f"🗑️  Eliminando Tablas del Esquema ML")
    print("=" * 60)
    print(f"Base de datos: Neon (cloud)")
    print(f"Esquema: {schema_name}")
    print()
    
    # Crear engine
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            # Verificar si el esquema existe
            check_schema_query = text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = :schema_name
            """)
            result = conn.execute(check_schema_query, {"schema_name": schema_name})
            schema_exists = result.fetchone() is not None
            
            if not schema_exists:
                print(f"⚠️  El esquema '{schema_name}' no existe")
                return
            
            # Obtener todas las tablas del esquema
            get_tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema_name
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            result = conn.execute(get_tables_query, {"schema_name": schema_name})
            tables = [row[0] for row in result.fetchall()]
            
            if not tables:
                print(f"✅ El esquema '{schema_name}' ya está vacío (no hay tablas)")
                return
            
            print(f"📋 Tablas encontradas en el esquema '{schema_name}':")
            for table in tables:
                print(f"   - {table}")
            print()
            
            # Confirmar eliminación
            print("⚠️  ADVERTENCIA: Se eliminarán todas las tablas del esquema ML")
            print("   Esto no se puede deshacer.")
            print()
            
            # Eliminar tablas en orden inverso (para respetar foreign keys)
            # Primero eliminar tablas que tienen foreign keys
            tables_to_drop = [
                "predictions_validation",
                "feature_importance",
                "model_evaluations",
                "training_runs",
                "experiments"
            ]
            
            # Solo eliminar las tablas que existen
            tables_to_drop = [t for t in tables_to_drop if t in tables]
            
            if tables_to_drop:
                print("🗑️  Eliminando tablas...")
                for table in tables_to_drop:
                    try:
                        drop_query = text(f"DROP TABLE IF EXISTS {schema_name}.{table} CASCADE")
                        conn.execute(drop_query)
                        print(f"   ✅ Tabla '{table}' eliminada")
                    except Exception as e:
                        print(f"   ❌ Error al eliminar tabla '{table}': {e}")
                
                conn.commit()
                print()
            
            # Verificar si quedan tablas
            result = conn.execute(get_tables_query, {"schema_name": schema_name})
            remaining_tables = [row[0] for row in result.fetchall()]
            
            if remaining_tables:
                print(f"⚠️  Aún quedan {len(remaining_tables)} tablas:")
                for table in remaining_tables:
                    print(f"   - {table}")
                print("   (Puede que tengan nombres diferentes)")
            else:
                print("=" * 60)
                print("✅ Esquema ML limpiado exitosamente")
                print("=" * 60)
                print()
                print("📝 El esquema está listo para definir nuevas tablas")
                print()
            
    except Exception as e:
        print(f"❌ Error al eliminar tablas: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Función principal"""
    drop_ml_tables()


if __name__ == "__main__":
    main()

