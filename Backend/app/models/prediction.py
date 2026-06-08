"""
Prediction model for RF-06 and RF-07
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class Prediction(SysBase):
    """Prediction model for ML predictions with telemetry"""
    
    __tablename__ = "predictions"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("app.requests.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    model_version_id = Column(Integer, ForeignKey("app.model_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    score = Column(Text, nullable=False)  # JSON con el score de la predicción
    latency_ms = Column(Float, nullable=True)  # Latencia de la predicción en ms
    telemetry = Column(Text, nullable=True)  # JSON con telemetría adicional
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    request = relationship("Request", foreign_keys=[request_id])
    model_version = relationship("ModelVersion", foreign_keys=[model_version_id])
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, request_id={self.request_id}, model_version_id={self.model_version_id})>"

