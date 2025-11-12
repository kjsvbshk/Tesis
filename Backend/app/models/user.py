"""
User model for NBA Bets application
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class User(SysBase):
    """User model for virtual betting system"""
    
    __tablename__ = "users"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(20), default="usuario", nullable=False)  # Rol legacy - mantener por compatibilidad
    credits = Column(Float, default=1000.0, nullable=False)  # Virtual credits
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    roles = relationship("Role", secondary="app.user_roles", back_populates="users")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', rol='{self.rol}', credits={self.credits})>"
