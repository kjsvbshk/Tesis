"""
Database configuration and session management
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Engine para Neon (esquema app) - Sistema de usuarios/apuestas
# Neon no soporta search_path en conexiones pooled, se establece después de conectar
app_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG,
    # No usar search_path en connect_args para Neon pooled connections
)

# Engine para Neon (esquema espn) - Datos de NBA
espn_engine = create_engine(
    settings.NBA_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG,
    # No usar search_path en connect_args para Neon pooled connections
)

# Session factories
AppSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)
EspnSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=espn_engine)

# Bases separadas para cada esquema
AppBase = declarative_base()
EspnBase = declarative_base()

# Dependencias para obtener sesiones
def get_app_db():
    """Dependency para Neon (esquema app)"""
    db = AppSessionLocal()
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
    """Dependency para Neon (esquema espn)"""
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

# Aliases para compatibilidad con código existente (mantener sys_* por compatibilidad)
sys_engine = app_engine
SysSessionLocal = AppSessionLocal
SysBase = AppBase
get_sys_db = get_app_db

# Para compatibilidad con código existente (usa app por defecto)
get_db = get_app_db
engine = app_engine
Base = AppBase
SessionLocal = AppSessionLocal
