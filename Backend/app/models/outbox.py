"""
Outbox model for RF-08
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import SysBase

class Outbox(SysBase):
    """Outbox model for transactional event publishing"""
    
    __tablename__ = "outbox"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(100), nullable=False, index=True)  # e.g., "prediction.completed", "bet.placed"
    payload = Column(Text, nullable=False)  # JSON con el payload del evento
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)  # NULL = no publicado
    
    def __repr__(self):
        return f"<Outbox(id={self.id}, topic='{self.topic}', published_at={self.published_at})>"

