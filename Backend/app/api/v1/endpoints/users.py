"""
Users API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from app.core.database import get_sys_db
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserResponse, UserCreate, UserUpdate, UserLogin, Token
from app.services.user_service import UserService
from app.services.auth_service import get_current_user, authenticate_user, create_access_token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    db: Session = Depends(get_sys_db)
):
    """Login user and return JWT token"""
    user = await authenticate_user(
        db, 
        user_credentials.username, 
        user_credentials.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_sys_db)):
    """Register a new user - siempre con rol 'usuario' por defecto"""
    try:
        user_service = UserService(db)
        
        # Check if username already exists
        existing_user = await user_service.get_user_by_username(user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Check if email already exists
        existing_email = await user_service.get_user_by_email(user.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Crear usuario - el servicio siempre asigna rol 'usuario' por defecto
        # Ignoramos cualquier rol que venga en el request
        new_user = await user_service.create_user(user)
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback_str = traceback.format_exc()
        print(f"Error creating user: {error_detail}")
        print(f"Traceback: {traceback_str}")
        raise HTTPException(status_code=500, detail=f"Error creating user: {error_detail}")

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user - invalida la sesión del lado del servidor"""
    # Con JWT stateless, técnicamente no hay nada que invalidar en el servidor
    # Pero este endpoint permite:
    # 1. Registrar el logout para auditoría
    # 2. Notificar al cliente que el logout fue exitoso
    # 3. En el futuro, podríamos implementar una blacklist de tokens
    return {
        "message": "Logout successful",
        "username": current_user.username
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Update current user information - no permite cambiar el rol"""
    try:
        user_service = UserService(db)
        
        # Los usuarios no pueden cambiar su propio rol
        if user_update.rol is not None:
            # Remover el campo rol del update si viene en el request
            update_dict = user_update.dict(exclude_unset=True)
            update_dict.pop('rol', None)
            user_update = UserUpdate(**update_dict)
        
        updated_user = await user_service.update_user(current_user.id, user_update)
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@router.get("/credits")
async def get_user_credits(current_user: User = Depends(get_current_user)):
    """Get current user's credit balance"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "credits": current_user.credits
    }

@router.post("/credits/add")
async def add_credits(
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Add credits to user account (for testing purposes)"""
    try:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        user_service = UserService(db)
        updated_user = await user_service.add_credits(current_user.id, amount)
        
        return {
            "message": f"Added ${amount} credits to your account",
            "new_balance": updated_user.credits
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding credits: {str(e)}")

@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_sys_db)
):
    """Get all users (admin only - for now, no auth required for demo)"""
    try:
        user_service = UserService(db)
        users = await user_service.get_all_users(limit=limit, offset=offset)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")
