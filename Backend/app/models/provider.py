"""
Provider model for RF-05 and RF-18
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class Provider(SysBase):
    """Provider model for external data providers"""
    
    __tablename__ = "providers"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "espn", "odds_api"
    name = Column(String(100), nullable=False)  # e.g., "ESPN API", "Odds API"
    is_active = Column(Boolean, default=True, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)  # Timeout por defecto
    max_retries = Column(Integer, default=3, nullable=False)  # Máximo de reintentos
    circuit_breaker_threshold = Column(Integer, default=5, nullable=False)  # Umbral para circuit breaker
    provider_metadata = Column(Text, nullable=True)  # JSON con configuración adicional (renombrado de 'metadata' porque es reservado)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    endpoints = relationship("ProviderEndpoint", back_populates="provider", cascade="all, delete-orphan")
    odds_lines = relationship("OddsLine", back_populates="provider")
    
    def __repr__(self):
        return f"<Provider(id={self.id}, code='{self.code}', is_active={self.is_active})>"

