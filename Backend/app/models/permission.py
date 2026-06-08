"""
Permission model for authorization system
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class Permission(SysBase):
    """Permission model for RBAC system"""
    
    __tablename__ = "permissions"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "predictions:read", "bets:write"
    name = Column(String(200), nullable=False)  # e.g., "Read Predictions", "Create Bets"
    description = Column(Text, nullable=True)
    scope = Column(String(50), nullable=True)  # e.g., "predictions", "bets", "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    roles = relationship("Role", secondary="app.role_permissions", back_populates="permissions")
    
    def __repr__(self):
        return f"<Permission(id={self.id}, code='{self.code}', scope='{self.scope}')>"

