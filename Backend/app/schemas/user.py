"""
User Pydantic schemas
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date

class UserBase(BaseModel):
    username: str
    email: EmailStr
    rol: str  # Rol obligatorio (client, administrator, operator)

class UserCreate(BaseModel):
    """Schema para crear usuario - username, email y password son requeridos"""
    username: str
    email: EmailStr
    password: str
    # Nota: el rol siempre será 'usuario' por defecto, no se acepta en el request

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    rol: Optional[str] = None
    credits: Optional[float] = None
    # Client profile fields
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    # Frontend sends 'birth_date', we'll handle mapping in the endpoint
    birth_date: Optional[str] = None

class UserResponse(UserBase):
    id: int
    credits: Optional[float] = None  # Opcional, solo para clientes
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    avatar_url: Optional[str] = None  # Avatar URL
    # Client profile fields (optional)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    
    class Config:
        from_attributes = True

class UserCreateWithRol(UserBase):
    """Schema para crear usuario con rol explícito (solo admin)"""
    password: str
    rol: str = "usuario"  # Por defecto usuario, pero puede ser especificado

class UserLogin(BaseModel):
    username: str
    password: str
    two_factor_code: Optional[str] = None  # Required if 2FA is enabled

class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str  # Rol del usuario (client, administrator, operator)

class SendVerificationCodeRequest(BaseModel):
    """Request to send verification code"""
    email: EmailStr
    purpose: str = "registration"  # 'registration' or 'password_reset'

class VerifyCodeRequest(BaseModel):
    """Request to verify code"""
    email: Optional[EmailStr] = None  # Required for registration, optional for password_reset
    username: Optional[str] = None  # Required for password_reset, optional for registration
    code: str
    purpose: str = "registration"

class RegisterWithVerificationRequest(BaseModel):
    """Register user after email verification"""
    username: str
    email: EmailStr
    password: str
    verification_code: str

class ForgotPasswordRequest(BaseModel):
    """Request password reset - sends verification code to email associated with username"""
    username: str

class ResetPasswordRequest(BaseModel):
    """Reset password after code verification"""
    username: str
    code: str
    new_password: str

# ============================================================================
# Two-Factor Authentication Schemas
# ============================================================================

class TwoFactorSetupResponse(BaseModel):
    """Response for 2FA setup - contains QR code data and backup codes"""
    secret: str
    qr_code_url: str  # Data URL for QR code image
    backup_codes: List[str]  # List of backup codes (only shown once)
    
class TwoFactorVerifyRequest(BaseModel):
    """Request to verify 2FA code during setup"""
    code: str
    
class TwoFactorEnableRequest(BaseModel):
    """Request to enable 2FA after verification"""
    code: str
    
class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA"""
    password: str  # Require password confirmation
    
class TwoFactorStatusResponse(BaseModel):
    """Response with 2FA status"""
    is_enabled: bool
    is_setup: bool  # True if secret exists but not enabled yet
    
# ============================================================================
# Avatar Schemas
# ============================================================================

class AvatarUploadResponse(BaseModel):
    """Response after avatar upload"""
    avatar_url: str
    message: str

# ============================================================================
# Session Schemas
# ============================================================================

class UserSessionResponse(BaseModel):
    """Response for user session information"""
    id: int
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    last_activity: datetime
    created_at: datetime
    is_current: bool = False  # True if this is the current session
    
    class Config:
        from_attributes = True

class SessionRevokeRequest(BaseModel):
    """Request to revoke a session"""
    session_id: int
