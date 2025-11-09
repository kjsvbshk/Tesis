"""
Configuration settings for the NBA Bets API
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://postgres:admin@localhost:5432/nba_data"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "nba_data"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "admin"
    
    # JWT Configuration
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ESPN API Configuration
    ESPN_API_KEY: Optional[str] = None
    ESPN_BASE_URL: str = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
    
    # Model Configuration
    MODEL_PATH: str = "ml/models/"
    FEATURES_PATH: str = "data/processed/features.csv"
    
    # Virtual Credits Configuration
    INITIAL_CREDITS: float = 1000.0
    MIN_BET_AMOUNT: float = 1.0
    MAX_BET_AMOUNT: float = 100.0
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()
