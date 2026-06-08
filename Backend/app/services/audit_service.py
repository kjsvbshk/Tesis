"""
Audit Service for RF-09 (RF-10 en doc.txt)
Registra todas las acciones relevantes del sistema
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from app.models import AuditLog


class AuditService:
    """Service for comprehensive audit logging"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def log_action(
        self,
        action: str,
        actor_user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        organization_id: Optional[int] = None,
        commit: bool = True
    ) -> AuditLog:
        """
        Registra una acción en el log de auditoría
        """
        audit_log = AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before=json.dumps(before) if before else None,
            after=json.dumps(after) if after else None,
            audit_metadata=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        
        if commit:
            self.db.commit()
            self.db.refresh(audit_log)
        else:
            self.db.flush()
        
        return audit_log
    
    # Métodos helper para acciones comunes
    async def log_user_action(
        self,
        action: str,
        actor_user_id: int,
        user_id: int,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = True
    ) -> AuditLog:
        """Registra una acción sobre un usuario"""
        return await self.log_action(
            action=action,
            actor_user_id=actor_user_id,
            resource_type="user",
            resource_id=user_id,
            before=before,
            after=after,
            metadata=metadata,
            commit=commit
        )
    
    async def log_bet_action(
        self,
        action: str,
        actor_user_id: int,
        bet_id: int,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = True
    ) -> AuditLog:
        """Registra una acción sobre una apuesta"""
        return await self.log_action(
            action=action,
            actor_user_id=actor_user_id,
            resource_type="bet",
            resource_id=bet_id,
            before=before,
            after=after,
            metadata=metadata,
            commit=commit
        )
    
    async def log_prediction_action(
        self,
        action: str,
        actor_user_id: int,
        prediction_id: int,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = True
    ) -> AuditLog:
        """Registra una acción sobre una predicción"""
        return await self.log_action(
            action=action,
            actor_user_id=actor_user_id,
            resource_type="prediction",
            resource_id=prediction_id,
            before=before,
            after=after,
            metadata=metadata,
            commit=commit
        )
    
    async def log_request_action(
        self,
        action: str,
        actor_user_id: Optional[int],
        request_id: int,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = True
    ) -> AuditLog:
        """Registra una acción sobre un request"""
        return await self.log_action(
            action=action,
            actor_user_id=actor_user_id,
            resource_type="request",
            resource_id=request_id,
            before=before,
            after=after,
            metadata=metadata,
            commit=commit
        )
    
    async def get_audit_logs(
        self,
        actor_user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Obtiene logs de auditoría con filtros"""
        query = self.db.query(AuditLog)
        
        if actor_user_id:
            query = query.filter(AuditLog.actor_user_id == actor_user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        if date_from:
            query = query.filter(AuditLog.created_at >= date_from)
        if date_to:
            query = query.filter(AuditLog.created_at <= date_to)
        
        return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    
    async def get_audit_log_by_id(self, audit_log_id: int) -> Optional[AuditLog]:
        """Obtiene un log de auditoría por ID"""
        return self.db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()

