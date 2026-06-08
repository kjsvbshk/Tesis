"""
Model Version model for RF-06
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class ModelVersion(SysBase):
    """Model Version model for ML model versioning"""
    
    __tablename__ = "model_versions"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "v1.0.0", "v1.1.0"
    is_active = Column(Boolean, default=False, nullable=False)  # Solo una versión activa
    model_metadata = Column(Text, nullable=True)  # JSON con metadatos del modelo (renombrado de 'metadata' porque es reservado)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    predictions = relationship("Prediction", back_populates="model_version")
    
    def __repr__(self):
        return f"<ModelVersion(id={self.id}, version='{self.version}', is_active={self.is_active})>"

