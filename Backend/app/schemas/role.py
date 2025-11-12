"""
Role schemas for RBAC
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class RoleBase(BaseModel):
    """Base role schema"""
    code: str = Field(..., min_length=1, max_length=50, description="Role code (e.g., 'admin', 'user')")
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, description="Role description")

class RoleCreate(RoleBase):
    """Schema for creating a role"""
    pass

class RoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class RoleResponse(RoleBase):
    """Schema for role response"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class RoleWithPermissions(RoleResponse):
    """Role with permissions"""
    permissions: List["PermissionResponse"] = []

