"""
User-Role association table
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from app.core.database import SysBase

class UserRole(SysBase):
    """Association table between users and roles"""
    
    __tablename__ = "user_roles"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app.user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("app.roles.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id}, is_active={self.is_active})>"

