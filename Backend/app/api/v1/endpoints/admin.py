"""
Admin endpoints for RBAC management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_sys_db
from app.models import User
from app.services.auth_service import get_current_user
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from app.schemas.permission import PermissionCreate, PermissionUpdate, PermissionResponse
from app.core.authorization import get_user_permissions, has_permission

router = APIRouter()

def require_admin_permission(current_user: User = Depends(get_current_user), db: Session = Depends(get_sys_db)):
    """Dependency to require admin permission"""
    user_permissions = get_user_permissions(db, current_user.id)
    if not has_permission("admin:write", user_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    return current_user

# ========== Roles ==========

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role: RoleCreate,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Create a new role (admin only)"""
    try:
        role_service = RoleService(db)
        new_role = await role_service.create_role(
            code=role.code,
            name=role.name,
            description=role.description
        )
        return new_role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating role: {str(e)}")

@router.get("/roles", response_model=List[RoleResponse])
async def get_all_roles(
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Get all roles (admin only)"""
    try:
        role_service = RoleService(db)
        roles = await role_service.get_all_roles(limit=limit, offset=offset)
        return roles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching roles: {str(e)}")

@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Get a specific role (admin only)"""
    try:
        role_service = RoleService(db)
        role = await role_service.get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching role: {str(e)}")

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Update a role (admin only)"""
    try:
        role_service = RoleService(db)
        updated_role = await role_service.update_role(
            role_id=role_id,
            name=role_update.name,
            description=role_update.description
        )
        if not updated_role:
            raise HTTPException(status_code=404, detail="Role not found")
        return updated_role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating role: {str(e)}")

@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Delete a role (admin only)"""
    try:
        role_service = RoleService(db)
        success = await role_service.delete_role(role_id)
        if not success:
            raise HTTPException(status_code=404, detail="Role not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting role: {str(e)}")

@router.post("/roles/{role_id}/permissions/{permission_id}", status_code=status.HTTP_201_CREATED)
async def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Assign a permission to a role (admin only)"""
    try:
        role_service = RoleService(db)
        success = await role_service.assign_permission_to_role(role_id, permission_id)
        if not success:
            raise HTTPException(status_code=400, detail="Permission already assigned to role")
        return {"message": "Permission assigned to role successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning permission: {str(e)}")

@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Remove a permission from a role (admin only)"""
    try:
        role_service = RoleService(db)
        success = await role_service.remove_permission_from_role(role_id, permission_id)
        if not success:
            raise HTTPException(status_code=404, detail="Permission not assigned to role")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing permission: {str(e)}")

# ========== Permissions ==========

@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission: PermissionCreate,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Create a new permission (admin only)"""
    try:
        permission_service = PermissionService(db)
        new_permission = await permission_service.create_permission(
            code=permission.code,
            name=permission.name,
            description=permission.description,
            scope=permission.scope
        )
        return new_permission
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating permission: {str(e)}")

@router.get("/permissions", response_model=List[PermissionResponse])
async def get_all_permissions(
    limit: int = 50,
    offset: int = 0,
    scope: str = None,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Get all permissions (admin only)"""
    try:
        permission_service = PermissionService(db)
        permissions = await permission_service.get_all_permissions(limit=limit, offset=offset, scope=scope)
        return permissions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching permissions: {str(e)}")

@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Get a specific permission (admin only)"""
    try:
        permission_service = PermissionService(db)
        permission = await permission_service.get_permission_by_id(permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        return permission
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching permission: {str(e)}")

@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Update a permission (admin only)"""
    try:
        permission_service = PermissionService(db)
        updated_permission = await permission_service.update_permission(
            permission_id=permission_id,
            name=permission_update.name,
            description=permission_update.description,
            scope=permission_update.scope
        )
        if not updated_permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        return updated_permission
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating permission: {str(e)}")

@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Delete a permission (admin only)"""
    try:
        permission_service = PermissionService(db)
        success = await permission_service.delete_permission(permission_id)
        if not success:
            raise HTTPException(status_code=404, detail="Permission not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting permission: {str(e)}")

# ========== User Roles ==========

@router.post("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Assign a role to a user (admin only)"""
    try:
        from app.models import UserRole
        
        # Verificar si el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verificar si el rol existe
        role_service = RoleService(db)
        role = await role_service.get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        # Verificar si ya tiene el rol asignado
        existing = db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ).first()
        
        if existing:
            # Si existe pero está inactivo, activarlo
            if not existing.is_active:
                existing.is_active = True
                db.commit()
                # Sincronizar campo legacy
                role_service.sync_legacy_rol(user_id)
                return {"message": "Role activated for user"}
            raise HTTPException(status_code=400, detail="Role already assigned to user")
        
        # Crear nueva asignación
        user_role = UserRole(user_id=user_id, role_id=role_id, is_active=True)
        db.add(user_role)
        db.commit()
        db.refresh(user_role)
        
        # Sincronizar campo legacy
        role_service.sync_legacy_rol(user_id)
        
        return {"message": "Role assigned to user successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error assigning role: {str(e)}")

@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Remove a role from a user (admin only)"""
    try:
        from app.models import UserRole
        
        user_role = db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ).first()
        
        if not user_role:
            raise HTTPException(status_code=404, detail="Role not assigned to user")
        
        # Desactivar en lugar de eliminar (soft delete)
        user_role.is_active = False
        db.commit()
        
        # Sincronizar campo legacy
        role_service = RoleService(db)
        role_service.sync_legacy_rol(user_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing role: {str(e)}")

@router.get("/users/{user_id}/roles", response_model=List[RoleResponse])
async def get_user_roles(
    user_id: int,
    admin_user: User = Depends(require_admin_permission),
    db: Session = Depends(get_sys_db)
):
    """Get all roles for a user (admin only)"""
    try:
        role_service = RoleService(db)
        roles = await role_service.get_user_roles(user_id)
        return roles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user roles: {str(e)}")

