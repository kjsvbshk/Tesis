"""
Provider Endpoint model for RF-05
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class ProviderEndpoint(SysBase):
    """Provider Endpoint model for external API endpoints"""
    
    __tablename__ = "provider_endpoints"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("app.providers.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(100), nullable=False)  # e.g., "odds", "stats", "predictions"
    url = Column(String(500), nullable=False)
    method = Column(String(10), default="GET", nullable=False)  # GET, POST, etc.
    headers = Column(Text, nullable=True)  # JSON con headers adicionales
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    provider = relationship("Provider", back_populates="endpoints")
    
    def __repr__(self):
        return f"<ProviderEndpoint(id={self.id}, provider_id={self.provider_id}, purpose='{self.purpose}')>"

