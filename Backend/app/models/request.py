"""
Request model for RF-03 - ACID transaction registration
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase
import enum

class RequestStatus(str, enum.Enum):
    """Request status enumeration"""
    RECEIVED = "received"
    PROCESSING = "processing"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"

class Request(SysBase):
    """Request model for ACID transaction registration"""
    
    __tablename__ = "requests"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=True)  # Para futuro uso con organizaciones
    user_id = Column(Integer, ForeignKey("app.user_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    event_id = Column(Integer, nullable=True)  # Referencia a espn.games.id (sin FK por esquema diferente)
    market_id = Column(Integer, nullable=True)  # Para futuro uso con markets
    request_key = Column(String(255), nullable=False, index=True)  # Referencia a idempotency_keys.request_key
    status = Column(Enum(RequestStatus), default=RequestStatus.RECEIVED, nullable=False, index=True)
    request_metadata = Column(Text, nullable=True)  # JSON con metadatos adicionales (renombrado de 'metadata' porque es reservado)
    error_message = Column(Text, nullable=True)  # Mensaje de error si falla
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("UserAccount", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<Request(id={self.id}, request_key='{self.request_key}', status='{self.status}')>"

