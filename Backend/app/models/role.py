"""
Role model for authorization system
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class Role(SysBase):
    """Role model for RBAC system"""
    
    __tablename__ = "roles"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "admin", "user", "operator"
    name = Column(String(100), nullable=False)  # e.g., "Administrator", "Regular User"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    permissions = relationship("Permission", secondary="app.role_permissions", back_populates="roles")
    users = relationship("UserAccount", secondary="app.user_roles", back_populates="roles")
    
    def __repr__(self):
        return f"<Role(id={self.id}, code='{self.code}', name='{self.name}')>"

