"""
Normalized User Account models - Separated by user type
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey, Date, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

# ============================================================================
# Tabla Base de Cuentas de Usuario
# ============================================================================

class UserAccount(SysBase):
    """Base user account with common authentication fields"""
    
    __tablename__ = "user_accounts"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # avatar_url movido a tablas individuales (clients/administrators/operators)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships (polymorphic)
    client = relationship("Client", back_populates="user_account", uselist=False)
    administrator = relationship("Administrator", back_populates="user_account", uselist=False)
    operator = relationship("Operator", back_populates="user_account", uselist=False)
    roles = relationship("Role", secondary="app.user_roles", back_populates="users")
    
    def __repr__(self):
        return f"<UserAccount(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def user_type(self):
        """Determine user type based on relationships"""
        if self.client:
            return 'client'
        elif self.administrator:
            return 'administrator'
        elif self.operator:
            return 'operator'
        return None


# ============================================================================
# Cliente (Reemplaza "usuario")
# ============================================================================

class Client(SysBase):
    """Client model - Users who can place bets"""
    
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint('credits >= 0', name='chk_clients_credits_positive'),
        {'schema': 'app'},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_account_id = Column(Integer, ForeignKey("app.user_accounts.id", ondelete="CASCADE"), nullable=False, unique=True)
    role_id = Column(Integer, ForeignKey("app.roles.id", ondelete="RESTRICT"), nullable=False)
    
    # Client-specific fields
    credits = Column(Numeric(10, 2), default=1000.0, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    avatar_url = Column(String(500), nullable=True)  # URL o path del avatar
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_account = relationship("UserAccount", foreign_keys=[user_account_id], back_populates="client")
    role = relationship("Role", foreign_keys=[role_id])
    
    def __repr__(self):
        return f"<Client(id={self.id}, user_account_id={self.user_account_id}, credits={self.credits})>"


# ============================================================================
# Administrador
# ============================================================================

class Administrator(SysBase):
    """Administrator model - System administrators with full access"""
    
    __tablename__ = "administrators"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_account_id = Column(Integer, ForeignKey("app.user_accounts.id", ondelete="CASCADE"), nullable=False, unique=True)
    role_id = Column(Integer, ForeignKey("app.roles.id", ondelete="RESTRICT"), nullable=False)
    
    # Administrator-specific fields
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=True)
    department = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)  # URL o path del avatar
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_account = relationship("UserAccount", foreign_keys=[user_account_id], back_populates="administrator")
    role = relationship("Role", foreign_keys=[role_id])
    
    def __repr__(self):
        return f"<Administrator(id={self.id}, user_account_id={self.user_account_id}, employee_id='{self.employee_id}')>"


# ============================================================================
# Operador
# ============================================================================

class Operator(SysBase):
    """Operator model - System operators with limited permissions"""
    
    __tablename__ = "operators"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_account_id = Column(Integer, ForeignKey("app.user_accounts.id", ondelete="CASCADE"), nullable=False, unique=True)
    role_id = Column(Integer, ForeignKey("app.roles.id", ondelete="RESTRICT"), nullable=False)
    
    # Operator-specific fields
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=True)
    department = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    shift = Column(String(50), nullable=True)  # Work shift: "mañana", "tarde", "noche"
    avatar_url = Column(String(500), nullable=True)  # URL o path del avatar
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_account = relationship("UserAccount", foreign_keys=[user_account_id], back_populates="operator")
    role = relationship("Role", foreign_keys=[role_id])
    
    def __repr__(self):
        return f"<Operator(id={self.id}, user_account_id={self.user_account_id}, employee_id='{self.employee_id}', shift='{self.shift}')>"

