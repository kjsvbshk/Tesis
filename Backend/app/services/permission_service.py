"""
Permission service for RBAC management
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import Permission, Role

class PermissionService:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        """Get permission by ID"""
        return self.db.query(Permission).filter(Permission.id == permission_id).first()
    
    async def get_permission_by_code(self, code: str) -> Optional[Permission]:
        """Get permission by code"""
        return self.db.query(Permission).filter(Permission.code == code).first()
    
    async def get_all_permissions(self, limit: int = 50, offset: int = 0, scope: Optional[str] = None) -> List[Permission]:
        """Get all permissions with optional scope filter"""
        query = self.db.query(Permission)
        if scope:
            query = query.filter(Permission.scope == scope)
        return query.offset(offset).limit(limit).all()
    
    async def create_permission(self, code: str, name: str, description: Optional[str] = None, scope: Optional[str] = None) -> Permission:
        """Create a new permission"""
        # Verificar si ya existe
        existing = await self.get_permission_by_code(code)
        if existing:
            raise ValueError(f"Permission with code '{code}' already exists")
        
        permission = Permission(code=code, name=name, description=description, scope=scope)
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission
    
    async def update_permission(self, permission_id: int, name: Optional[str] = None, description: Optional[str] = None, scope: Optional[str] = None) -> Optional[Permission]:
        """Update a permission"""
        permission = await self.get_permission_by_id(permission_id)
        if not permission:
            return None
        
        if name is not None:
            permission.name = name
        if description is not None:
            permission.description = description
        if scope is not None:
            permission.scope = scope
        
        self.db.commit()
        self.db.refresh(permission)
        return permission
    
    async def delete_permission(self, permission_id: int) -> bool:
        """Delete a permission"""
        permission = await self.get_permission_by_id(permission_id)
        if not permission:
            return False
        
        self.db.delete(permission)
        self.db.commit()
        return True
    
    async def get_permission_roles(self, permission_id: int) -> List[Role]:
        """Get all roles that have this permission"""
        permission = await self.get_permission_by_id(permission_id)
        if not permission:
            return []
        
        return permission.roles

