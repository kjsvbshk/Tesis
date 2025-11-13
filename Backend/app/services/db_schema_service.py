"""
Database Schema Service
Inspecciona la estructura real de las tablas en la base de datos
para hacer consultas dinámicas basadas en las columnas reales
"""

from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from typing import Dict, List, Optional
from functools import lru_cache


class DBSchemaService:
    """Service para inspeccionar la estructura real de las tablas"""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache = {}
    
    def get_table_columns(self, table_name: str, schema: str = 'espn') -> Dict[str, str]:
        """
        Obtiene las columnas reales de una tabla con sus tipos de dato
        Retorna un diccionario {column_name: data_type}
        """
        cache_key = f"{schema}.{table_name}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Consultar information_schema para obtener columnas reales
            result = self.db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = :schema AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"schema": schema, "table_name": table_name})
            
            columns_data = result.fetchall()
            columns_dict = {row[0]: row[1] for row in columns_data}
            
            if columns_dict:
                print(f"✅ Found {len(columns_dict)} columns in {schema}.{table_name}: {list(columns_dict.keys())}")
                self._cache[cache_key] = columns_dict
                return columns_dict
            
            # Fallback: intentar con inspector de SQLAlchemy
            try:
                inspector = inspect(self.db.bind)
                columns = inspector.get_columns(table_name, schema=schema)
                columns_dict = {col['name']: str(col.get('type', '')) for col in columns}
                if columns_dict:
                    print(f"✅ Found {len(columns_dict)} columns in {schema}.{table_name} (via inspector): {list(columns_dict.keys())}")
                    self._cache[cache_key] = columns_dict
                    return columns_dict
            except Exception as e:
                print(f"⚠️  Inspector fallback failed: {e}")
            
            print(f"⚠️  No columns found for {schema}.{table_name}")
            return {}
            
        except Exception as e:
            print(f"❌ Error inspecting table {schema}.{table_name}: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def find_column(self, table_name: str, possible_names: List[str], schema: str = 'espn') -> Optional[str]:
        """
        Busca una columna por nombres posibles
        Retorna el nombre real de la columna si existe, None si no se encuentra
        """
        columns = self.get_table_columns(table_name, schema)
        
        for name in possible_names:
            if name in columns:
                return name
        
        # Buscar case-insensitive
        columns_lower = {k.lower(): k for k in columns.keys()}
        for name in possible_names:
            if name.lower() in columns_lower:
                return columns_lower[name.lower()]
        
        return None
    
    def get_all_tables_in_schema(self, schema: str = 'espn') -> List[str]:
        """Obtiene todas las tablas en un esquema"""
        try:
            result = self.db.execute(text("""
                SELECT table_name
                FROM information_schema.tables 
                WHERE table_schema = :schema
                ORDER BY table_name
            """), {"schema": schema})
            
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            print(f"❌ Error getting tables in schema {schema}: {e}")
            return []
    
    def table_exists(self, table_name: str, schema: str = 'espn') -> bool:
        """Verifica si una tabla existe"""
        try:
            result = self.db.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables 
                WHERE table_schema = :schema AND table_name = :table_name
            """), {"schema": schema, "table_name": table_name})
            
            return result.scalar() > 0
        except Exception as e:
            print(f"❌ Error checking if table exists {schema}.{table_name}: {e}")
            return False
    
    def clear_cache(self):
        """Limpia la caché de columnas"""
        self._cache.clear()

