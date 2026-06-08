"""
Authorization utilities for RBAC
"""

from typing import List, Optional
from functools import wraps
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_sys_db
from app.models import UserAccount, UserRole, Permission, Role
from app.services.auth_service import get_current_user

def get_user_permissions(db: Session, user_id: int) -> List[str]:
    """Get all permission codes for a user"""
    # Obtener roles activos del usuario
    user_roles = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.is_active == True
    ).all()
    
    if not user_roles:
        return []
    
    role_ids = [ur.role_id for ur in user_roles]
    
    # Obtener permisos de los roles usando la tabla intermedia role_permissions
    from app.models import RolePermission
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(
        RolePermission.role_id.in_(role_ids)
    ).distinct().all()
    
    return [perm.code for perm in permissions]

def get_user_scopes(db: Session, user_id: int) -> List[str]:
    """Get all unique scopes for a user"""
    permissions = get_user_permissions(db, user_id)
    scopes = set()
    
    for perm_code in permissions:
        # Extraer scope del código (formato: "scope:action")
        if ':' in perm_code:
            scope = perm_code.split(':')[0]
            scopes.add(scope)
    
    return list(scopes)

def has_permission(permission_code: str, user_permissions: List[str]) -> bool:
    """Check if user has a specific permission"""
    return permission_code in user_permissions

def has_scope(scope: str, user_scopes: List[str]) -> bool:
    """Check if user has access to a scope"""
    return scope in user_scopes

def require_permission(permission_code: str):
    """Dependency factory to require a specific permission"""
    async def permission_checker(
        current_user: UserAccount = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
    ) -> UserAccount:
        """Check if user has required permission"""
        user_permissions = get_user_permissions(db, current_user.id)
        
        if not has_permission(permission_code, user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_code}' required"
            )
        
        return current_user
    
    return permission_checker

def require_scope(scope: str):
    """Dependency factory to require access to a scope"""
    async def scope_checker(
        current_user: UserAccount = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
    ) -> UserAccount:
        """Check if user has access to required scope"""
        user_scopes = get_user_scopes(db, current_user.id)
        
        if not has_scope(scope, user_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to scope '{scope}' required"
            )
        
        return current_user
    
    return scope_checker

async def get_current_user_with_permissions(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
) -> UserAccount:
    """Get current user with permissions loaded"""
    # Los permisos se cargan bajo demanda cuando se necesitan
    # Esto evita cargar datos innecesarios en cada request
    return current_user

