"""
User Session models for tracking active JWT sessions
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class UserSession(SysBase):
    """Active user sessions (JWT tokens)"""
    
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index('idx_user_sessions_user_account_id', 'user_account_id'),
        Index('idx_user_sessions_token_hash', 'token_hash'),
        {'schema': 'app'},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_account_id = Column(Integer, ForeignKey("app.user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Session information
    token_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of JWT token
    device_info = Column(String(255), nullable=True)  # Browser, OS, etc.
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)  # City, Country
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user_account = relationship("UserAccount", foreign_keys=[user_account_id])
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_account_id={self.user_account_id}, is_active={self.is_active})>"
