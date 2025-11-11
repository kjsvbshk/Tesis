"""
Configuration settings for the NBA Bets API
Todas las configuraciones se leen desde el archivo .env
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings - Lee desde .env"""
    
    # Database Configuration - App (Sistema de usuarios/apuestas)
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_SCHEMA: str
    DB_SSLMODE: str = "require"
    DB_CHANNEL_BINDING: str = "require"
    
    # Database Configuration - NBA Data (Datos de ESPN)
    NBA_DB_HOST: str
    NBA_DB_PORT: int = 5432
    NBA_DB_NAME: str
    NBA_DB_USER: str
    NBA_DB_PASSWORD: str
    NBA_DB_SCHEMA: str
    NBA_DB_SSLMODE: str = "require"
    NBA_DB_CHANNEL_BINDING: str = "require"
    
    @property
    def DATABASE_URL(self) -> str:
        """Construye la URL de conexión para la base de datos app"""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?sslmode={self.DB_SSLMODE}&channel_binding={self.DB_CHANNEL_BINDING}"
        )
    
    @property
    def NBA_DATABASE_URL(self) -> str:
        """Construye la URL de conexión para la base de datos nba_data"""
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

# Create settings instance
settings = Settings()
