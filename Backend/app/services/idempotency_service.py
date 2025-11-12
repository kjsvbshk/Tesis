"""
Idempotency service for RF-02
Handles request deduplication using request_key
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.models import IdempotencyKey, Request
from app.core.config import settings

class IdempotencyService:
    def __init__(self, db: Session):
        self.db = db
        self.default_ttl_hours = 24  # TTL por defecto: 24 horas
    
    async def check_idempotency_key(self, request_key: str) -> Optional[Dict[str, Any]]:
        """
        Verificar si existe una clave de idempotencia previa
        Retorna None si no existe, o el resultado previo si existe
        """
        idempotency_key = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.request_key == request_key
        ).first()
        
        if not idempotency_key:
            return None
        
        # Verificar si expiró
        if idempotency_key.expires_at and idempotency_key.expires_at < datetime.utcnow():
            # Eliminar clave expirada
            self.db.delete(idempotency_key)
            self.db.commit()
            return None
        
        # Si existe y no expiró, retornar respuesta previa
        if idempotency_key.response_data:
            import json
            try:
                return {
                    "exists": True,
                    "response": json.loads(idempotency_key.response_data),
                    "created_at": idempotency_key.created_at
                }
            except:
                return {
                    "exists": True,
                    "response": idempotency_key.response_data,
                    "created_at": idempotency_key.created_at
                }
        
        return {"exists": True, "created_at": idempotency_key.created_at}
    
    async def create_idempotency_key(
        self,
        request_key: str,
        request_id: Optional[int] = None,
        ttl_hours: Optional[int] = None
    ) -> IdempotencyKey:
        """
        Crear una nueva clave de idempotencia
        """
        # Verificar si ya existe
        existing = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.request_key == request_key
        ).first()
        
        if existing:
            # Actualizar request_id si se proporciona
            if request_id:
                existing.request_id = request_id
                self.db.commit()
                self.db.refresh(existing)
            return existing
        
        # Calcular fecha de expiración
        expires_at = None
        if ttl_hours:
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        elif self.default_ttl_hours:
            expires_at = datetime.utcnow() + timedelta(hours=self.default_ttl_hours)
        
        # Crear nueva clave
        idempotency_key = IdempotencyKey(
            request_key=request_key,
            request_id=request_id,
            expires_at=expires_at
        )
        
        self.db.add(idempotency_key)
        self.db.commit()
        self.db.refresh(idempotency_key)
        
        return idempotency_key
    
    async def store_response(
        self,
        request_key: str,
        response_data: Dict[str, Any]
    ) -> bool:
        """
        Almacenar respuesta para una clave de idempotencia
        """
        idempotency_key = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.request_key == request_key
        ).first()
        
        if not idempotency_key:
            return False
        
        # Serializar respuesta a JSON
        import json
        try:
            idempotency_key.response_data = json.dumps(response_data)
        except:
            idempotency_key.response_data = str(response_data)
        
        self.db.commit()
        return True
    
    async def delete_idempotency_key(self, request_key: str) -> bool:
        """
        Eliminar una clave de idempotencia
        """
        idempotency_key = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.request_key == request_key
        ).first()
        
        if not idempotency_key:
            return False
        
        self.db.delete(idempotency_key)
        self.db.commit()
        return True
    
    async def cleanup_expired_keys(self) -> int:
        """
        Limpiar claves de idempotencia expiradas
        Retorna el número de claves eliminadas
        """
        now = datetime.utcnow()
        expired_keys = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.expires_at < now
        ).all()
        
        count = len(expired_keys)
        for key in expired_keys:
            self.db.delete(key)
        
        self.db.commit()
        return count

