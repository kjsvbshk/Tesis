"""
Role service for RBAC management
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import Role, Permission, RolePermission, UserRole, UserAccount

class RoleService:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """Get role by ID"""
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    async def get_role_by_code(self, code: str) -> Optional[Role]:
        """Get role by code"""
        return self.db.query(Role).filter(Role.code == code).first()
    
    async def get_all_roles(self, limit: int = 50, offset: int = 0) -> List[Role]:
        """Get all roles with pagination"""
        return self.db.query(Role).offset(offset).limit(limit).all()
    
    async def create_role(self, code: str, name: str, description: Optional[str] = None) -> Role:
        """Create a new role"""
        # Verificar si ya existe
        existing = await self.get_role_by_code(code)
        if existing:
            raise ValueError(f"Role with code '{code}' already exists")
        
        role = Role(code=code, name=name, description=description)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role
    
    async def update_role(self, role_id: int, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Role]:
        """Update a role"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return None
        
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        
        self.db.commit()
        self.db.refresh(role)
        return role
    
    async def delete_role(self, role_id: int) -> bool:
        """Delete a role"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return False
        
        self.db.delete(role)
        self.db.commit()
        return True
    
    async def assign_permission_to_role(self, role_id: int, permission_id: int) -> bool:
        """Assign a permission to a role"""
        # Verificar si ya existe la relación
        existing = self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        ).first()
        
        if existing:
            return False  # Ya existe
        
        role_perm = RolePermission(role_id=role_id, permission_id=permission_id)
        self.db.add(role_perm)
        self.db.commit()
        return True
    
    async def remove_permission_from_role(self, role_id: int, permission_id: int) -> bool:
        """Remove a permission from a role"""
        role_perm = self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        ).first()
        
        if not role_perm:
            return False
        
        self.db.delete(role_perm)
        self.db.commit()
        return True
    
    async def get_role_permissions(self, role_id: int) -> List[Permission]:
        """Get all permissions for a role"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return []
        
        return role.permissions
    
    async def get_user_roles(self, user_id: int) -> List[Role]:
        """Get all roles for a user"""
        user = self.db.query(UserAccount).filter(UserAccount.id == user_id).first()
        if not user:
            return []
        
        # Obtener roles activos
        user_roles = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.is_active == True
        ).all()
        
        return [self.db.query(Role).filter(Role.id == ur.role_id).first() for ur in user_roles if ur.role_id]
    
