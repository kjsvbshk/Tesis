"""
Idempotency Key model for RF-02
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import SysBase

class IdempotencyKey(SysBase):
    """Idempotency Key model for duplicate request detection"""
    
    __tablename__ = "idempotency_keys"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    request_key = Column(String(255), unique=True, nullable=False, index=True)
    request_id = Column(Integer, nullable=True)  # FK a requests.id (se agregará después)
    response_data = Column(Text, nullable=True)  # Respuesta previa en JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Para limpiar keys antiguas
    
    def __repr__(self):
        return f"<IdempotencyKey(id={self.id}, request_key='{self.request_key}')>"

