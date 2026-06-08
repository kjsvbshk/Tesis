"""
Partial Response utilities for RF-10
Permite respuestas parciales con metadatos de degradación
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class PartialResponse:
    """Helper para construir respuestas parciales con metadatos de degradación"""
    
    def __init__(
        self,
        data: Any,
        errors: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.data = data
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.is_partial = len(self.errors) > 0 or len(self.warnings) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la respuesta parcial a diccionario"""
        response = {
            "data": self.data,
            "is_partial": self.is_partial,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.errors:
            response["errors"] = self.errors
            response["degradation"] = {
                "level": "error" if len(self.errors) > 0 else "warning",
                "affected_components": [e.get("component", "unknown") for e in self.errors],
                "message": f"{len(self.errors)} component(s) failed"
            }
        
        if self.warnings:
            response["warnings"] = self.warnings
        
        if self.metadata:
            response["metadata"] = self.metadata
        
        return response
    
    @classmethod
    def success(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "PartialResponse":
        """Crea una respuesta exitosa completa"""
        return cls(data=data, metadata=metadata)
    
    @classmethod
    def partial(
        cls,
        data: Any,
        errors: List[Dict[str, Any]],
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "PartialResponse":
        """Crea una respuesta parcial con errores"""
        return cls(data=data, errors=errors, warnings=warnings, metadata=metadata)
    
    @classmethod
    def error(
        cls,
        error_message: str,
        component: str = "unknown",
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "PartialResponse":
        """Crea una respuesta de error"""
        error = {
            "message": error_message,
            "component": component,
            "timestamp": datetime.utcnow().isoformat()
        }
        if error_code:
            error["code"] = error_code
        
        return cls(
            data=None,
            errors=[error],
            metadata=metadata
        )


def create_degradation_metadata(
    failed_components: List[str],
    successful_components: List[str],
    partial_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Crea metadatos de degradación"""
    return {
        "degradation": {
            "level": "partial" if len(successful_components) > 0 else "error",
            "failed_components": failed_components,
            "successful_components": successful_components,
            "total_components": len(failed_components) + len(successful_components),
            "success_rate": len(successful_components) / (len(failed_components) + len(successful_components)) if (len(failed_components) + len(successful_components)) > 0 else 0
        },
        "partial_data": partial_data or {}
    }

