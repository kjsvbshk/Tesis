"""
Configuration settings for the NBA Bets API
Todas las configuraciones se leen desde el archivo .env
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional

class Settings(BaseSettings):
    """Application settings - Lee desde .env"""
    
    # Database Configuration - App (Sistema de usuarios/apuestas)
    # Usar variables de Neon directamente
    DB_HOST: str = None  # Se sobrescribe con NEON_DB_HOST si está disponible
    DB_PORT: int = 5432
    DB_NAME: str = None  # Se sobrescribe con NEON_DB_NAME si está disponible
    DB_USER: str = None  # Se sobrescribe con NEON_DB_USER si está disponible
    DB_PASSWORD: str = None  # Se sobrescribe con NEON_DB_PASSWORD si está disponible
    DB_SCHEMA: str = "app"  # Esquema app en Neon
    DB_SSLMODE: str = "require"
    DB_CHANNEL_BINDING: str = "require"
    
    # Database Configuration - NBA Data (Datos de ESPN)
    # Usar variables de Neon directamente
    NBA_DB_HOST: str = None  # Se sobrescribe con NEON_DB_HOST si está disponible
    NBA_DB_PORT: int = 5432
    NBA_DB_NAME: str = None  # Se sobrescribe con NEON_DB_NAME si está disponible
    NBA_DB_USER: str = None  # Se sobrescribe con NEON_DB_USER si está disponible
    NBA_DB_PASSWORD: str = None  # Se sobrescribe con NEON_DB_PASSWORD si está disponible
    NBA_DB_SCHEMA: str = "espn"  # Esquema espn en Neon
    NBA_DB_SSLMODE: str = "require"
    NBA_DB_CHANNEL_BINDING: str = "require"
    
    # Neon Database Connection (prioridad sobre DB_*)
    NEON_DB_HOST: str = None
    NEON_DB_PORT: int = 5432
    NEON_DB_NAME: str = None
    NEON_DB_USER: str = None
    NEON_DB_PASSWORD: str = None
    NEON_DB_SSLMODE: str = "require"
    NEON_DB_CHANNEL_BINDING: str = "require"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Si hay variables de Neon, usarlas para sobrescribir DB_*
        if self.NEON_DB_HOST:
            self.DB_HOST = self.NEON_DB_HOST
        if self.NEON_DB_PORT:
            self.DB_PORT = self.NEON_DB_PORT
        if self.NEON_DB_NAME:
            self.DB_NAME = self.NEON_DB_NAME
        if self.NEON_DB_USER:
            self.DB_USER = self.NEON_DB_USER
        if self.NEON_DB_PASSWORD:
            self.DB_PASSWORD = self.NEON_DB_PASSWORD
        if self.NEON_DB_SSLMODE:
            self.DB_SSLMODE = self.NEON_DB_SSLMODE
        if self.NEON_DB_CHANNEL_BINDING:
            self.DB_CHANNEL_BINDING = self.NEON_DB_CHANNEL_BINDING
        
        # Si se usan variables de Neon, usar esquema "app" por defecto
        if self.NEON_DB_HOST and self.DB_SCHEMA == "sys":
            self.DB_SCHEMA = "app"
        
        # Para NBA también usar Neon
        if self.NEON_DB_HOST:
            self.NBA_DB_HOST = self.NEON_DB_HOST
        if self.NEON_DB_PORT:
            self.NBA_DB_PORT = self.NEON_DB_PORT
        if self.NEON_DB_NAME:
            self.NBA_DB_NAME = self.NEON_DB_NAME
        if self.NEON_DB_USER:
            self.NBA_DB_USER = self.NEON_DB_USER
        if self.NEON_DB_PASSWORD:
            self.NBA_DB_PASSWORD = self.NEON_DB_PASSWORD
        if self.NEON_DB_SSLMODE:
            self.NBA_DB_SSLMODE = self.NEON_DB_SSLMODE
        if self.NEON_DB_CHANNEL_BINDING:
            self.NBA_DB_CHANNEL_BINDING = self.NEON_DB_CHANNEL_BINDING
    
    @property
    def DATABASE_URL(self) -> str:
        """Construye la URL de conexión para la base de datos app (Neon)"""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?sslmode={self.DB_SSLMODE}&channel_binding={self.DB_CHANNEL_BINDING}"
        )
    
    @property
    def NBA_DATABASE_URL(self) -> str:
        """Construye la URL de conexión para la base de datos nba_data (Neon)"""
        return (
            f"postgresql://{self.NBA_DB_USER}:{self.NBA_DB_PASSWORD}@"
            f"{self.NBA_DB_HOST}:{self.NBA_DB_PORT}/{self.NBA_DB_NAME}"
            f"?sslmode={self.NBA_DB_SSLMODE}&channel_binding={self.NBA_DB_CHANNEL_BINDING}"
        )
    
    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    @field_validator('DEBUG', mode='before')
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG value - handles string values like 'WARN', 'INFO', etc."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            # Convert string to lowercase for comparison
            v_lower = v.lower().strip()
            # Only 'true', '1', 'yes', 'on' are considered True
            if v_lower in ('true', '1', 'yes', 'on', 'enabled'):
                return True
            # Everything else (including 'WARN', 'INFO', 'ERROR', etc.) is False
            return False
        # For other types, try to convert to bool
        try:
            return bool(v)
        except:
            return False
     
    # Virtual Credits Configuration (opcional)
    INITIAL_CREDITS: Optional[float] = 1000.0
    MIN_BET_AMOUNT: Optional[float] = 1.0
    MAX_BET_AMOUNT: Optional[float] = 100.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignora variables extra como DATABASE_URL y NBA_DATABASE_URL si existen
        # Las variables de entorno tienen prioridad sobre el .env
        env_ignore_empty = True

# Create settings instance con manejo de errores de codificación
try:
    settings = Settings()
except UnicodeDecodeError:
    # Si hay error de codificación en .env, intentar con otras codificaciones
    import os
    from dotenv import load_dotenv
    
    # Intentar cargar .env con diferentes codificaciones
    encodings = ['latin-1', 'cp1252', 'iso-8859-1']
    loaded = False
    
    for encoding in encodings:
        try:
            if os.path.exists('.env'):
                load_dotenv('.env', encoding=encoding)
                loaded = True
                break
        except:
            continue
    
    # Si no se pudo cargar, usar variables de entorno del sistema
    if not loaded:
        print("⚠️  Advertencia: No se pudo cargar .env, usando variables de entorno del sistema")
    
    # Crear settings sin .env (solo variables de entorno)
    class SettingsWithoutEnv(Settings):
        class Config:
            env_file = None  # No cargar .env
            case_sensitive = True
            extra = "ignore"
            env_ignore_empty = True
    
    settings = SettingsWithoutEnv()
