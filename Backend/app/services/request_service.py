"""
Request service for RF-03
Handles ACID transaction registration for requests
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
from app.models import Request, RequestStatus

class RequestService:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_request(
        self,
        request_key: str,
        user_id: Optional[int] = None,
        event_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        market_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Request:
        """
        Crear un nuevo registro de solicitud (ACID transaction)
        Estado inicial: RECEIVED
        """
        # Serializar metadata a JSON si se proporciona
        request_metadata = None
        if metadata:
            import json
            try:
                request_metadata = json.dumps(metadata)
            except:
                request_metadata = str(metadata)
        
        request = Request(
            request_key=request_key,
            user_id=user_id,
            event_id=event_id,
            organization_id=organization_id,
            market_id=market_id,
            status=RequestStatus.RECEIVED,
            request_metadata=request_metadata
        )
        
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    async def get_request_by_id(self, request_id: int) -> Optional[Request]:
        """Obtener request por ID"""
        return self.db.query(Request).filter(Request.id == request_id).first()
    
    async def get_request_by_key(self, request_key: str) -> Optional[Request]:
        """Obtener request por request_key"""
        return self.db.query(Request).filter(Request.request_key == request_key).first()
    
    async def update_request_status(
        self,
        request_id: int,
        status: RequestStatus,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Request]:
        """
        Actualizar el estado de una solicitud
        """
        request = await self.get_request_by_id(request_id)
        if not request:
            return None
        
        request.status = status
        request.updated_at = datetime.utcnow()
        
        if error_message:
            request.error_message = error_message
        
        if metadata:
            import json
            try:
                # Actualizar metadata existente o crear nuevo
                if request.request_metadata:
                    existing_metadata = json.loads(request.request_metadata)
                    existing_metadata.update(metadata)
                    request.request_metadata = json.dumps(existing_metadata)
                else:
                    request.request_metadata = json.dumps(metadata)
            except:
                request.request_metadata = str(metadata)
        
        # Si el estado es COMPLETED o FAILED, marcar completed_at
        if status in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
            request.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    async def mark_request_processing(self, request_id: int) -> Optional[Request]:
        """Marcar request como en procesamiento"""
        return await self.update_request_status(request_id, RequestStatus.PROCESSING)
    
    async def mark_request_partial(self, request_id: int, metadata: Optional[Dict[str, Any]] = None) -> Optional[Request]:
        """Marcar request como parcial (algunos proveedores fallaron)"""
        return await self.update_request_status(request_id, RequestStatus.PARTIAL, metadata=metadata)
    
    async def mark_request_completed(self, request_id: int, metadata: Optional[Dict[str, Any]] = None) -> Optional[Request]:
        """Marcar request como completada"""
        return await self.update_request_status(request_id, RequestStatus.COMPLETED, metadata=metadata)
    
    async def mark_request_failed(self, request_id: int, error_message: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Request]:
        """Marcar request como fallida"""
        return await self.update_request_status(request_id, RequestStatus.FAILED, error_message=error_message, metadata=metadata)
    
    async def get_user_requests(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[RequestStatus] = None
    ) -> list[Request]:
        """Obtener requests de un usuario"""
        query = self.db.query(Request).filter(Request.user_id == user_id)
        
        if status:
            query = query.filter(Request.status == status)
        
        return query.order_by(Request.created_at.desc()).offset(offset).limit(limit).all()
    
    async def search_requests(
        self,
        request_key: Optional[str] = None,
        user_id: Optional[int] = None,
        event_id: Optional[int] = None,
        status: Optional[RequestStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Request]:
        """
        Buscar requests con múltiples filtros
        """
        query = self.db.query(Request)
        
        if request_key:
            query = query.filter(Request.request_key == request_key)
        if user_id:
            query = query.filter(Request.user_id == user_id)
        if event_id:
            query = query.filter(Request.event_id == event_id)
        if status:
            query = query.filter(Request.status == status)
        if date_from:
            query = query.filter(Request.created_at >= date_from)
        if date_to:
            query = query.filter(Request.created_at <= date_to)
        
        return query.order_by(Request.created_at.desc()).offset(offset).limit(limit).all()

