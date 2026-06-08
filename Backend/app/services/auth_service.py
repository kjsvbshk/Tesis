"""
Authentication service
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_sys_db
from app.models.user_accounts import UserAccount, Client, Administrator, Operator
from app.models.user_role import UserRole
from app.models.permission import Permission
# from app.services.user_service import UserService  # Removed to avoid circular import

# Password hashing - usando argon2 que es más seguro y sin límite de longitud
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password using argon2 (sin límite de longitud)"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return username"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_sys_db)
) -> UserAccount:
    """Get current authenticated user (UserAccount)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        username = verify_token(token)
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Direct database query to avoid circular import
    user_account = db.query(UserAccount).filter(UserAccount.username == username).first()
    if user_account is None:
        raise credentials_exception
    
    if not user_account.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user_account

async def authenticate_user(db: Session, username: str, password: str) -> Optional[UserAccount]:
    """Authenticate user with username and password"""
    # Direct database query to avoid circular import
    user_account = db.query(UserAccount).filter(UserAccount.username == username).first()
    if not user_account:
        return None
    if not verify_password(password, user_account.hashed_password):
        return None
    return user_account
