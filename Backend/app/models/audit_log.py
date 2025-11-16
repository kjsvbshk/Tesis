"""
Audit Log model for RF-10
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import SysBase

class AuditLog(SysBase):
    """Audit Log model for complete audit trail"""
    
    __tablename__ = "audit_log"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=True)  # Para futuro uso con organizaciones
    actor_user_id = Column(Integer, ForeignKey("app.user_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., "create_user", "place_bet", "update_prediction"
    resource_type = Column(String(50), nullable=True)  # e.g., "user", "bet", "prediction"
    resource_id = Column(Integer, nullable=True)  # ID del recurso afectado
    before = Column(Text, nullable=True)  # JSON con estado anterior
    after = Column(Text, nullable=True)  # JSON con estado nuevo
    audit_metadata = Column(Text, nullable=True)  # JSON con metadatos adicionales (renombrado de 'metadata' porque es reservado)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', actor_user_id={self.actor_user_id})>"

