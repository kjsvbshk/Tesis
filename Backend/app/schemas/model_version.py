from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, Union
import json
from datetime import datetime

class ModelVersionBase(BaseModel):
    version: str
    is_active: bool = False
    model_metadata: Optional[Union[Dict[str, Any], str]] = None

    @field_validator('model_metadata', mode='before')
    @classmethod
    def parse_metadata(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v

class ModelVersionCreate(ModelVersionBase):
    pass

class ModelVersionResponse(ModelVersionBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
