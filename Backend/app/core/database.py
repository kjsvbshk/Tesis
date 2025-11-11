"""
Database configuration and session management
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Engine para BD data (esquema app) - Sistema de usuarios/apuestas
# Neon no soporta search_path en conexiones pooled, se establece después de conectar
sys_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG,
    # No usar search_path en connect_args para Neon pooled connections
)

# Engine para BD data (esquema espn) - Datos de NBA
espn_engine = create_engine(
    settings.NBA_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG,
    # No usar search_path en connect_args para Neon pooled connections
)

# Session factories
SysSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sys_engine)
EspnSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=espn_engine)

# Bases separadas para cada esquema
SysBase = declarative_base()
EspnBase = declarative_base()

# Dependencias para obtener sesiones
def get_sys_db():
    """Dependency para BD data (esquema app)"""
    db = SysSessionLocal()
    try:
        # Establecer search_path después de conectar (Neon no soporta en pooled)
        # Usar execute con commit explícito
        from sqlalchemy import text
        db.execute(text(f"SET search_path TO {settings.DB_SCHEMA}, public"))
        db.commit()
        yield db
    finally:
        db.close()

def get_espn_db():
    """Dependency para BD data (esquema espn)"""
    db = EspnSessionLocal()
    try:
        # Establecer search_path después de conectar (Neon no soporta en pooled)
        # Usar execute con commit explícito
        from sqlalchemy import text
        db.execute(text(f"SET search_path TO {settings.NBA_DB_SCHEMA}, public"))
        db.commit()
        yield db
    finally:
        db.close()

# Para compatibilidad con código existente (usa sys por defecto)
get_db = get_sys_db
engine = sys_engine
Base = SysBase
SessionLocal = SysSessionLocal
