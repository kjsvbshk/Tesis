"""
User Pydantic schemas
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

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

class UserResponse(UserBase):
    id: int
    credits: Optional[float] = None  # Opcional, solo para clientes
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserCreateWithRol(UserBase):
    """Schema para crear usuario con rol explícito (solo admin)"""
    password: str
    rol: str = "usuario"  # Por defecto usuario, pero puede ser especificado

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str  # Rol del usuario (client, administrator, operator)
