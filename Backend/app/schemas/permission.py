"""
Permission schemas for RBAC
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PermissionBase(BaseModel):
    """Base permission schema"""
    code: str = Field(..., min_length=1, max_length=100, description="Permission code (e.g., 'predictions:read')")
    name: str = Field(..., min_length=1, max_length=200, description="Permission name")
    description: Optional[str] = Field(None, description="Permission description")
    scope: Optional[str] = Field(None, max_length=50, description="Permission scope (e.g., 'predictions', 'bets')")

class PermissionCreate(PermissionBase):
    """Schema for creating a permission"""
    pass

class PermissionUpdate(BaseModel):
    """Schema for updating a permission"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    scope: Optional[str] = Field(None, max_length=50)

class PermissionResponse(PermissionBase):
    """Schema for permission response"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

