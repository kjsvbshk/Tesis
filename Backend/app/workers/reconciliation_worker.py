"""
Reconciliation Worker
Verifica integridad referencial entre espn.bets.user_id y app.user_accounts.id
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import SysSessionLocal, sys_engine
from app.core.config import settings

logger = logging.getLogger(__name__)


class ReconciliationWorker:
    """Worker para verificar integridad referencial entre espn.bets y app.user_accounts"""
    
    def __init__(self, sys_db: Session = None):
        self.sys_db = sys_db or SysSessionLocal()
        self.running = False
        # Intervalo de ejecución: diario (86400 segundos) o configurable
        self.reconciliation_interval = getattr(settings, 'RECONCILIATION_INTERVAL', 86400)  # Default: 24 horas
    
    async def start(self):
        """Inicia el worker con ejecución periódica"""
        self.running = True
        logger.info(f"Reconciliation worker started (interval: {self.reconciliation_interval}s / {self.reconciliation_interval/3600:.1f} hours)")
        
        while self.running:
            try:
                await self.reconcile_bets_user_accounts()
                await asyncio.sleep(self.reconciliation_interval)
            except Exception as e:
                logger.error(f"Error in reconciliation worker: {e}", exc_info=True)
                # En caso de error, esperar 1 hora antes de reintentar
                await asyncio.sleep(3600)
    
    async def stop(self):
        """Detiene el worker"""
        self.running = False
        logger.info("Reconciliation worker stopped")
    
    async def reconcile_bets_user_accounts(self) -> bool:
        """
        Verifica que todos los user_id en espn.bets tienen correspondencia en app.user_accounts
        Retorna True si no hay problemas, False si hay huérfanos
        """
        try:
            logger.info("Starting reconciliation: espn.bets.user_id ↔ app.user_accounts.id")
            
            # Query para encontrar bets huérfanas (cross-schema)
            # En Neon, ambos esquemas están en la misma base de datos
            query = text("""
                SELECT b.id, b.user_id, b.game_id, b.bet_amount, b.placed_at
                FROM espn.bets b
                LEFT JOIN app.user_accounts u ON u.id = b.user_id
                WHERE u.id IS NULL
                ORDER BY b.placed_at DESC
            """)
            
            # Ejecutar query cross-schema usando conexión directa
            # Establecer search_path para incluir ambos esquemas
            with sys_engine.connect() as conn:
                conn.execute(text("SET search_path TO app, espn, public"))
                conn.commit()
                orphaned_bets = conn.execute(query).fetchall()
            
            if orphaned_bets:
                orphan_count = len(orphaned_bets)
                logger.error(
                    f"❌ CRITICAL: Found {orphan_count} orphaned bets "
                    f"(bets with user_id not in user_accounts)"
                )
                
                # Log detalles de las primeras 10 bets huérfanas
                for i, bet in enumerate(orphaned_bets[:10], 1):
                    logger.error(
                        f"  Orphaned bet #{i}: id={bet.id}, user_id={bet.user_id}, "
                        f"game_id={bet.game_id}, amount={bet.bet_amount}, placed_at={bet.placed_at}"
                    )
                
                if orphan_count > 10:
                    logger.error(f"  ... and {orphan_count - 10} more orphaned bets")
                
                # Opcional: Enviar alerta o notificación
                # TODO: Integrar con sistema de alertas (email, Slack, etc.)
                
                return False
            else:
                logger.info("✅ Reconciliation successful: No orphaned bets found")
                return True
                
        except Exception as e:
            logger.error(f"Error during reconciliation: {e}", exc_info=True)
            return False
    
    async def run_once(self) -> bool:
        """
        Ejecuta una reconciliación única (útil para testing o ejecución manual)
        """
        return await self.reconcile_bets_user_accounts()


# Función helper para ejecutar reconciliación manualmente
async def run_reconciliation():
    """Ejecuta una reconciliación única"""
    worker = ReconciliationWorker()
    try:
        result = await worker.run_once()
        return result
    finally:
        worker.sys_db.close()


if __name__ == "__main__":
    # Para ejecutar como script standalone
    import sys
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        result = await run_reconciliation()
        sys.exit(0 if result else 1)
    
    asyncio.run(main())
