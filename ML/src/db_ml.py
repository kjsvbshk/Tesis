"""
Database connection and models for ML schema
Conexión a la base de datos usando el esquema ML en Neon
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional
from src.config import db_config

# Base para modelos del esquema ML
MLBase = declarative_base()


class MLDatabase:
    """Gestor de conexión a base de datos con esquema ML en Neon"""
    
    def __init__(self):
        """
        Inicializa la conexión a Neon con el esquema ML
        """
        self.schema = db_config.get_schema("ml")
        self.database_url = db_config.get_database_url()
        
        # Crear engine
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        
        # Session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def get_session(self):
        """
        Obtiene una sesión de base de datos con el esquema ML configurado
        
        Returns:
            Session de SQLAlchemy
        """
        session = self.SessionLocal()
        try:
            # Establecer search_path al esquema ML
            session.execute(text(f"SET search_path TO {self.schema}, public"))
            session.commit()
            return session
        except Exception as e:
            session.rollback()
            raise
    
    def create_tables(self):
        """Crea todas las tablas del esquema ML"""
        MLBase.metadata.create_all(bind=self.engine)
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a la base de datos
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            with self.engine.connect() as conn:
                # Establecer search_path
                conn.execute(text(f"SET search_path TO {self.schema}, public"))
                conn.commit()
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            return True
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False


# Instancia global
ml_db = MLDatabase()
