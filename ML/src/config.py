"""
Configuration settings for ML module
Lee las configuraciones desde el archivo .env (compartido con Backend)
Solo usa Neon (cloud), no bases de datos locales
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar .env - buscar en varios lugares comunes
# 1. Raíz del proyecto (Tesis/)
# 2. Backend/ (donde suele estar)
# 3. ML/ (por si acaso)
project_root = Path(__file__).parent.parent.parent
possible_env_paths = [
    project_root / ".env",           # Tesis/.env
    project_root / "Backend" / ".env",  # Tesis/Backend/.env
    Path(__file__).parent.parent / ".env",  # ML/.env
]

env_path = None
for path in possible_env_paths:
    if path.exists():
        env_path = path
        break

# Intentar cargar .env con diferentes codificaciones
if env_path:
    try:
        load_dotenv(env_path, encoding='utf-8')
        # No imprimir en cada import para evitar spam
    except UnicodeDecodeError:
        try:
            load_dotenv(env_path, encoding='latin-1')
        except:
            try:
                load_dotenv(env_path, encoding='cp1252')
            except:
                pass
else:
    # Intentar cargar desde variables de entorno del sistema
    pass

class DatabaseConfig:
    """Configuración de bases de datos - Solo Neon (cloud)"""
    
    # Neon Database (única base de datos usada)
    NEON_DB_HOST: Optional[str] = os.getenv("NEON_DB_HOST")
    NEON_DB_PORT: int = int(os.getenv("NEON_DB_PORT", "5432"))
    NEON_DB_NAME: Optional[str] = os.getenv("NEON_DB_NAME")
    NEON_DB_USER: Optional[str] = os.getenv("NEON_DB_USER")
    NEON_DB_PASSWORD: Optional[str] = os.getenv("NEON_DB_PASSWORD")
    NEON_DB_SSLMODE: str = os.getenv("NEON_DB_SSLMODE", "require")
    NEON_DB_CHANNEL_BINDING: str = os.getenv("NEON_DB_CHANNEL_BINDING", "require")
    
    # Esquemas en Neon
    ESPN_SCHEMA: str = os.getenv("NBA_DB_SCHEMA", "espn")  # Datos de NBA
    APP_SCHEMA: str = os.getenv("DB_SCHEMA", "sys")  # Datos del sistema
    ML_SCHEMA: str = os.getenv("ML_DB_SCHEMA", "ml")  # Esquema ML
    
    @classmethod
    def get_database_url(cls) -> str:
        """
        Construye la URL de conexión a Neon
        
        Returns:
            URL de conexión PostgreSQL a Neon
        """
        if not cls.NEON_DB_HOST:
            raise ValueError(
                "NEON_DB_HOST no está configurado. "
                "Asegúrate de tener las variables NEON_* en tu archivo .env"
            )
        
        return (
            f"postgresql://{cls.NEON_DB_USER}:{cls.NEON_DB_PASSWORD}@"
            f"{cls.NEON_DB_HOST}:{cls.NEON_DB_PORT}/{cls.NEON_DB_NAME}"
            f"?sslmode={cls.NEON_DB_SSLMODE}&channel_binding={cls.NEON_DB_CHANNEL_BINDING}"
        )
    
    @classmethod
    def get_schema(cls, schema_type: str = "espn") -> str:
        """
        Obtiene el esquema a usar
        
        Args:
            schema_type: Tipo de esquema - "espn", "app", o "ml"
        
        Returns:
            Nombre del esquema
        """
        schema_map = {
            "espn": cls.ESPN_SCHEMA,
            "app": cls.APP_SCHEMA,
            "sys": cls.APP_SCHEMA,  # Alias para compatibilidad
            "ml": cls.ML_SCHEMA,
        }
        return schema_map.get(schema_type, cls.ESPN_SCHEMA)


# Instancia global de configuración
db_config = DatabaseConfig()
