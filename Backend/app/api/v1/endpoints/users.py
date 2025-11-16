"""
Users API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from app.core.database import get_sys_db
from app.core.config import settings
from app.models.user_accounts import UserAccount, Client
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
    try:
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
        
        # Obtener el rol del usuario
        user_service = UserService(db)
        user_role = await user_service.get_user_role_code(user.id)
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User role not found"
            )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "rol": user_role
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback_str = traceback.format_exc()
        print(f"Error in login endpoint: {error_detail}")
        print(f"Traceback: {traceback_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during login: {error_detail}"
        )

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
        
        # Crear usuario - el servicio siempre asigna rol 'client' por defecto
        # Ignoramos cualquier rol que venga en el request
        new_user_account = await user_service.create_user(user)
        
        # Obtener información del cliente y el rol para la respuesta
        client = await user_service.get_client_by_user_id(new_user_account.id)
        user_role = await user_service.get_user_role_code(new_user_account.id)
        if not user_role:
            raise HTTPException(status_code=500, detail="User role not found")
        
        user_dict = {
            "id": new_user_account.id,
            "username": new_user_account.username,
            "email": new_user_account.email,
            "is_active": new_user_account.is_active,
            "credits": float(client.credits) if client else None,
            "rol": user_role,
            "created_at": new_user_account.created_at,
            "updated_at": new_user_account.updated_at
        }
        return user_dict
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
async def logout(current_user: UserAccount = Depends(get_current_user)):
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
async def get_current_user_info(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get current user information"""
    # Obtener información adicional según el tipo de usuario
    user_service = UserService(db)
    client = await user_service.get_client_by_user_id(current_user.id)
    user_role = await user_service.get_user_role_code(current_user.id)
    if not user_role:
        raise HTTPException(status_code=500, detail="User role not found")
    
    user_dict = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "credits": float(client.credits) if client else None,
        "rol": user_role,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }
    return user_dict

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Update current user information - no permite cambiar el rol"""
    try:
        user_service = UserService(db)
        
        # Los usuarios no pueden cambiar su propio rol
        if hasattr(user_update, 'rol') and user_update.rol is not None:
            # Remover el campo rol del update si viene en el request
            update_dict = user_update.dict(exclude_unset=True)
            update_dict.pop('rol', None)
            user_update = UserUpdate(**update_dict)
        
        updated_user = await user_service.update_user(current_user.id, user_update)
        
        # Obtener información del cliente y el rol para la respuesta
        client = await user_service.get_client_by_user_id(updated_user.id)
        user_role = await user_service.get_user_role_code(updated_user.id)
        if not user_role:
            raise HTTPException(status_code=500, detail="User role not found")
        
        user_dict = {
            "id": updated_user.id,
            "username": updated_user.username,
            "email": updated_user.email,
            "is_active": updated_user.is_active,
            "credits": float(client.credits) if client else None,
            "rol": user_role,
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at
        }
        return user_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@router.put("/me/password")
async def change_password(
    password_data: dict,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Change user password"""
    try:
        from app.services.auth_service import verify_password, get_password_hash
        
        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        
        if not current_password or not new_password:
            raise HTTPException(status_code=400, detail="current_password and new_password are required")
        
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters long")
        
        # Verify current password
        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        user_service = UserService(db)
        db_user = await user_service.get_user_by_id(current_user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_user.hashed_password = get_password_hash(new_password)
        db.commit()
        db.refresh(db_user)
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error changing password: {str(e)}")

@router.get("/me/permissions")
async def get_my_permissions(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get current user's permissions"""
    try:
        from app.core.authorization import get_user_permissions, get_user_scopes
        from app.services.role_service import RoleService
        
        # Obtener permisos y scopes del usuario
        permissions = get_user_permissions(db, current_user.id)
        scopes = get_user_scopes(db, current_user.id)
        
        # Obtener roles del usuario
        role_service = RoleService(db)
        roles = await role_service.get_user_roles(current_user.id)
        
        return {
            "user_id": current_user.id,
            "username": current_user.username,
            "roles": [{"id": r.id, "code": r.code, "name": r.name} for r in roles],
            "permissions": permissions,
            "scopes": scopes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching permissions: {str(e)}")

@router.get("/credits")
async def get_user_credits(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get current user's credit balance"""
    user_service = UserService(db)
    credits = await user_service.get_user_credits(current_user.id)
    
    if credits is None:
        raise HTTPException(status_code=404, detail="User is not a client or has no credits")
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "credits": credits
    }

@router.post("/credits/add")
async def add_credits(
    amount: float,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Add credits to user account (for testing purposes)"""
    try:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        user_service = UserService(db)
        success = await user_service.add_credits(current_user.id, amount)
        
        if not success:
            raise HTTPException(status_code=404, detail="User is not a client")
        
        new_balance = await user_service.get_user_credits(current_user.id)
        
        return {
            "message": f"Added ${amount} credits to your account",
            "new_balance": new_balance
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
        
        # Construir respuestas con todos los campos requeridos
        result = []
        for user_account in users:
            client = await user_service.get_client_by_user_id(user_account.id)
            user_role = await user_service.get_user_role_code(user_account.id)
            if not user_role:
                # Si no tiene rol, saltar este usuario o usar un valor por defecto
                continue
            
            user_dict = {
                "id": user_account.id,
                "username": user_account.username,
                "email": user_account.email,
                "is_active": user_account.is_active,
                "credits": float(client.credits) if client else None,
                "rol": user_role,
                "created_at": user_account.created_at,
                "updated_at": user_account.updated_at
            }
            result.append(user_dict)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")
