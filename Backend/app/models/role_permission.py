"""
Role-Permission association table
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import SysBase

class RolePermission(SysBase):
    """Association table between roles and permissions"""
    
    __tablename__ = "role_permissions"
    __table_args__ = {'schema': 'app'}
    
    role_id = Column(Integer, ForeignKey("app.roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("app.permissions.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"

