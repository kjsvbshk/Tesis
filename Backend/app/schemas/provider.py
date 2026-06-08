"""
Provider schemas for API requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProviderBase(BaseModel):
    code: str = Field(..., description="Unique provider code (e.g., 'espn', 'odds_api')")
    name: str = Field(..., description="Provider name")
    timeout_seconds: int = Field(30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    circuit_breaker_threshold: int = Field(5, ge=1, le=50, description="Circuit breaker failure threshold")
    provider_metadata: Optional[str] = Field(None, description="JSON metadata for provider configuration")

class ProviderCreate(ProviderBase):
    pass

class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    circuit_breaker_threshold: Optional[int] = Field(None, ge=1, le=50)
    provider_metadata: Optional[str] = None

class ProviderResponse(ProviderBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProviderEndpointBase(BaseModel):
    purpose: str = Field(..., description="Endpoint purpose (e.g., 'odds', 'stats', 'predictions')")
    url: str = Field(..., description="Endpoint URL")
    method: str = Field("GET", description="HTTP method")
    headers: Optional[str] = Field(None, description="JSON headers")

class ProviderEndpointCreate(ProviderEndpointBase):
    pass

class ProviderEndpointUpdate(BaseModel):
    purpose: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[str] = None

class ProviderEndpointResponse(BaseModel):
    id: int
    provider_id: int
    purpose: str
    url: str
    method: str
    headers: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ProviderStatusResponse(BaseModel):
    provider_code: str
    provider_id: int
    is_active: bool
    circuit_breaker: dict
