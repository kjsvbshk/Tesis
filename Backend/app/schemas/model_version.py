from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ModelVersionBase(BaseModel):
    version: str
    is_active: bool = False
    model_metadata: Optional[Dict[str, Any]] = None

class ModelVersionCreate(ModelVersionBase):
    pass

class ModelVersionResponse(ModelVersionBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
