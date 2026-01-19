"""
Outbox Worker for RF-08
Procesa eventos del outbox de forma asíncrona
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Outbox
from app.core.database import SysSessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Worker para procesar eventos del outbox con polling adaptivo"""
    
    def __init__(self, db: Session = None):
        self.db = db or SysSessionLocal()
        self.running = False
        # Usar intervalos configurables desde config
        self.poll_interval_with_events = settings.OUTBOX_POLL_INTERVAL  # Default: 5 segundos
        self.poll_interval_empty = settings.OUTBOX_POLL_INTERVAL_EMPTY  # Default: 30 segundos
    
    async def start(self):
        """Inicia el worker con polling adaptivo"""
        self.running = True
        logger.info(f"Outbox worker started (poll intervals: {self.poll_interval_with_events}s with events, {self.poll_interval_empty}s when empty)")
        
        while self.running:
            try:
                # Procesar eventos y obtener si había eventos
                had_events = await self.process_unpublished_events()
                
                # Usar intervalo corto si había eventos, largo si no había
                interval = self.poll_interval_with_events if had_events else self.poll_interval_empty
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in outbox worker: {e}", exc_info=True)
                # En caso de error, usar intervalo corto para reintentar pronto
                await asyncio.sleep(self.poll_interval_with_events)
    
    async def stop(self):
        """Detiene el worker"""
        self.running = False
        logger.info("Outbox worker stopped")
    
    async def process_unpublished_events(self, batch_size: int = None) -> bool:
        """
        Procesa eventos no publicados del outbox
        
        Returns:
            bool: True si había eventos para procesar, False si no había
        """
        if batch_size is None:
            batch_size = settings.OUTBOX_BATCH_SIZE
        
        try:
            # Obtener eventos no publicados
            unpublished = self.db.query(Outbox).filter(
                Outbox.published_at.is_(None)
            ).order_by(Outbox.created_at.asc()).limit(batch_size).all()
            
            if not unpublished:
                # No hay eventos, retornar False para usar intervalo largo
                return False
            
            # Hay eventos, procesarlos
            logger.info(f"Processing {len(unpublished)} unpublished event(s)")
            
            for event in unpublished:
                try:
                    await self.process_event(event)
                except Exception as e:
                    logger.error(f"Error processing event {event.id}: {e}", exc_info=True)
                    # No marcar como publicado si hay error
                    continue
            
            # Retornar True para indicar que había eventos (usar intervalo corto)
            return True
        except Exception as e:
            logger.error(f"Error fetching unpublished events: {e}", exc_info=True)
            self.db.rollback()
            # En caso de error, retornar False para no acelerar el polling
            return False
    
    async def process_event(self, event: Outbox):
        """Procesa un evento individual"""
        try:
            payload = json.loads(event.payload)
            topic = event.topic
            
            logger.debug(f"Processing event {event.id}: {topic}")
            
            # Procesar según el topic
            if topic == "prediction.completed":
                await self.handle_prediction_completed(payload)
            elif topic == "bet.placed":
                await self.handle_bet_placed(payload)
            elif topic == "request.completed":
                await self.handle_request_completed(payload)
            else:
                logger.warning(f"Unknown topic: {topic}")
            
            # Marcar como publicado
            event.published_at = datetime.utcnow()
            self.db.commit()
            logger.debug(f"Event {event.id} marked as published")
            
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def handle_prediction_completed(self, payload: dict):
        """Maneja evento de predicción completada"""
        # Aquí se podría enviar a un webhook, notificación, etc.
        logger.debug(f"Prediction completed: request_id={payload.get('request_id')}")
        # Por ahora solo logueamos, en el futuro se podría integrar con webhooks
    
    async def handle_bet_placed(self, payload: dict):
        """Maneja evento de apuesta colocada"""
        # Aquí se podría enviar a un webhook, notificación, etc.
        logger.debug(f"Bet placed: bet_id={payload.get('bet_id')}, user_id={payload.get('user_id')}")
        # Por ahora solo logueamos, en el futuro se podría integrar con webhooks
    
    async def handle_request_completed(self, payload: dict):
        """Maneja evento de request completado"""
        # Aquí se podría enviar a un webhook, notificación, etc.
        logger.debug(f"Request completed: request_id={payload.get('request_id')}")
        # Por ahora solo logueamos, en el futuro se podría integrar con webhooks
    
    async def process_single_event(self, event_id: int) -> bool:
        """Procesa un evento específico por ID"""
        event = self.db.query(Outbox).filter(Outbox.id == event_id).first()
        if not event:
            return False
        
        if event.published_at:
            logger.debug(f"Event {event_id} already published")
            return True
        
        try:
            await self.process_event(event)
            return True
        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}", exc_info=True)
            return False


# Instancia global del worker (se puede inicializar en background)
_worker: Optional[OutboxWorker] = None


async def start_outbox_worker():
    """Inicia el worker del outbox en background"""
    global _worker
    if _worker is None:
        _worker = OutboxWorker()
        asyncio.create_task(_worker.start())
    return _worker


async def stop_outbox_worker():
    """Detiene el worker del outbox"""
    global _worker
    if _worker:
        await _worker.stop()
        _worker = None

