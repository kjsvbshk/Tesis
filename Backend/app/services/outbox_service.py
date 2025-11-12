"""
Outbox Service for RF-08
Maneja eventos transaccionales usando el patrón outbox
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from app.models import Outbox


class OutboxService:
    """Service for transactional event publishing using outbox pattern"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def publish_event(
        self,
        topic: str,
        payload: Dict[str, Any],
        commit: bool = True
    ) -> Outbox:
        """
        Publica un evento en el outbox dentro de la misma transacción
        El evento se marcará como publicado cuando el worker lo procese
        """
        outbox_entry = Outbox(
            topic=topic,
            payload=json.dumps(payload),
            created_at=datetime.utcnow(),
            published_at=None  # Se actualiza cuando el worker lo procesa
        )
        
        self.db.add(outbox_entry)
        
        if commit:
            self.db.commit()
            self.db.refresh(outbox_entry)
        else:
            # Si no se hace commit, el evento se guardará cuando se haga commit de la transacción principal
            self.db.flush()
        
        return outbox_entry
    
    async def get_unpublished_events(
        self,
        limit: int = 100
    ) -> List[Outbox]:
        """Obtiene eventos no publicados para procesar"""
        return self.db.query(Outbox).filter(
            Outbox.published_at.is_(None)
        ).order_by(Outbox.created_at.asc()).limit(limit).all()
    
    async def mark_as_published(
        self,
        outbox_id: int,
        commit: bool = True
    ) -> bool:
        """Marca un evento como publicado"""
        outbox_entry = self.db.query(Outbox).filter(
            Outbox.id == outbox_id
        ).first()
        
        if not outbox_entry:
            return False
        
        outbox_entry.published_at = datetime.utcnow()
        
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        
        return True
    
    async def get_event_by_id(self, outbox_id: int) -> Optional[Outbox]:
        """Obtiene un evento por ID"""
        return self.db.query(Outbox).filter(Outbox.id == outbox_id).first()
    
    async def get_events_by_topic(
        self,
        topic: str,
        limit: int = 100,
        published_only: bool = False
    ) -> List[Outbox]:
        """Obtiene eventos por topic"""
        query = self.db.query(Outbox).filter(Outbox.topic == topic)
        
        if published_only:
            query = query.filter(Outbox.published_at.isnot(None))
        
        return query.order_by(Outbox.created_at.desc()).limit(limit).all()
    
    # Métodos helper para eventos comunes
    async def publish_prediction_completed(
        self,
        request_id: int,
        prediction_data: Dict[str, Any],
        commit: bool = True
    ) -> Outbox:
        """Publica evento de predicción completada"""
        payload = {
            "event_type": "prediction.completed",
            "request_id": request_id,
            "prediction": prediction_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self.publish_event("prediction.completed", payload, commit)
    
    async def publish_bet_placed(
        self,
        bet_id: int,
        user_id: int,
        bet_data: Dict[str, Any],
        commit: bool = True
    ) -> Outbox:
        """Publica evento de apuesta colocada"""
        payload = {
            "event_type": "bet.placed",
            "bet_id": bet_id,
            "user_id": user_id,
            "bet": bet_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self.publish_event("bet.placed", payload, commit)
    
    async def publish_request_completed(
        self,
        request_id: int,
        request_data: Dict[str, Any],
        commit: bool = True
    ) -> Outbox:
        """Publica evento de request completado"""
        payload = {
            "event_type": "request.completed",
            "request_id": request_id,
            "request": request_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self.publish_event("request.completed", payload, commit)

