"""
RBAC Service — merges RoleService + PermissionService
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import Role, Permission, RolePermission, UserRole, UserAccount


class RBACService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Roles                                                                #
    # ------------------------------------------------------------------ #

    async def get_role_by_id(self, role_id: int) -> Optional[Role]:
        return self.db.query(Role).filter(Role.id == role_id).first()

    async def get_role_by_code(self, code: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.code == code).first()

    async def get_all_roles(self, limit: int = 50, offset: int = 0) -> List[Role]:
        return self.db.query(Role).offset(offset).limit(limit).all()

    async def create_role(self, code: str, name: str, description: Optional[str] = None) -> Role:
        existing = await self.get_role_by_code(code)
        if existing:
            raise ValueError(f"Role with code '{code}' already exists")
        role = Role(code=code, name=name, description=description)
        self.db.add(role)
        return role

    async def update_role(self, role_id: int, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Role]:
        role = await self.get_role_by_id(role_id)
        if not role:
            return None
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        return role

    async def delete_role(self, role_id: int) -> bool:
        role = await self.get_role_by_id(role_id)
        if not role:
            return False
        self.db.delete(role)
        return True

    async def assign_permission_to_role(self, role_id: int, permission_id: int) -> bool:
        existing = self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        ).first()
        if existing:
            return False
        self.db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        return True

    async def remove_permission_from_role(self, role_id: int, permission_id: int) -> bool:
        rp = self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        ).first()
        if not rp:
            return False
        self.db.delete(rp)
        return True

    async def get_role_permissions(self, role_id: int) -> List[Permission]:
        role = await self.get_role_by_id(role_id)
        return role.permissions if role else []

    async def get_user_roles(self, user_id: int) -> List[Role]:
        return (
            self.db.query(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .filter(UserRole.user_id == user_id, UserRole.is_active == True)
            .all()
        )

    # ------------------------------------------------------------------ #
    # Permissions                                                          #
    # ------------------------------------------------------------------ #

    async def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        return self.db.query(Permission).filter(Permission.id == permission_id).first()

    async def get_permission_by_code(self, code: str) -> Optional[Permission]:
        return self.db.query(Permission).filter(Permission.code == code).first()

    async def get_all_permissions(self, limit: int = 50, offset: int = 0, scope: Optional[str] = None) -> List[Permission]:
        query = self.db.query(Permission)
        if scope:
            query = query.filter(Permission.scope == scope)
        return query.offset(offset).limit(limit).all()

    async def create_permission(self, code: str, name: str, description: Optional[str] = None, scope: Optional[str] = None) -> Permission:
        existing = await self.get_permission_by_code(code)
        if existing:
            raise ValueError(f"Permission with code '{code}' already exists")
        perm = Permission(code=code, name=name, description=description, scope=scope)
        self.db.add(perm)
        return perm

    async def update_permission(self, permission_id: int, name: Optional[str] = None, description: Optional[str] = None, scope: Optional[str] = None) -> Optional[Permission]:
        perm = await self.get_permission_by_id(permission_id)
        if not perm:
            return None
        if name is not None:
            perm.name = name
        if description is not None:
            perm.description = description
        if scope is not None:
            perm.scope = scope
        return perm

    async def delete_permission(self, permission_id: int) -> bool:
        perm = await self.get_permission_by_id(permission_id)
        if not perm:
            return False
        self.db.delete(perm)
        return True

    async def get_permission_roles(self, permission_id: int) -> List[Role]:
        perm = await self.get_permission_by_id(permission_id)
        return perm.roles if perm else []
