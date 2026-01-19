"""
Two-Factor Authentication models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class UserTwoFactor(SysBase):
    """Two-Factor Authentication configuration for users"""
    
    __tablename__ = "user_two_factor"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_account_id = Column(Integer, ForeignKey("app.user_accounts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # 2FA Configuration
    secret = Column(String(32), nullable=False)  # TOTP secret (base32 encoded)
    is_enabled = Column(Boolean, default=False, nullable=False)
    backup_codes = Column(Text, nullable=True)  # JSON array of backup codes (hashed)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    enabled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user_account = relationship("UserAccount", foreign_keys=[user_account_id])
    
    def __repr__(self):
        return f"<UserTwoFactor(id={self.id}, user_account_id={self.user_account_id}, is_enabled={self.is_enabled})>"
