"""
Provider tasks for RQ
Background tasks for provider synchronization and data fetching
"""

import logging
from sqlalchemy.orm import Session
from app.core.database import SysSessionLocal
from app.services.provider_orchestrator import ProviderOrchestrator

logger = logging.getLogger(__name__)


def sync_provider_data_task(provider_code: str, purpose: str = "odds"):
    """
    Background task to sync data from a provider
    This function is executed by RQ worker
    
    Args:
        provider_code: Provider code (e.g., 'espn')
        purpose: Purpose of the sync (e.g., 'odds', 'stats', 'matches')
    """
    try:
        db = SysSessionLocal()
        try:
            orchestrator = ProviderOrchestrator(db)
            
            # Run async function in sync context
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                orchestrator.call_provider(provider_code, purpose)
            )
            
            logger.info(f"✅ Provider sync completed: {provider_code}/{purpose}")
            return result
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Error syncing provider {provider_code}: {e}", exc_info=True)
        raise


def sync_all_providers_task(purpose: str = "odds"):
    """
    Background task to sync data from all active providers
    This function is executed by RQ worker
    
    Args:
        purpose: Purpose of the sync (e.g., 'odds', 'stats', 'matches')
    """
    try:
        db = SysSessionLocal()
        try:
            from app.models import Provider
            orchestrator = ProviderOrchestrator(db)
            
            # Get all active providers
            providers = db.query(Provider).filter(Provider.is_active == True).all()
            provider_codes = [p.code for p in providers]
            
            if not provider_codes:
                logger.warning("No active providers found")
                return {"message": "No active providers"}
            
            # Run async function in sync context
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                orchestrator.call_multiple_providers(provider_codes, purpose)
            )
            
            logger.info(f"✅ All providers sync completed: {purpose}")
            return result
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Error syncing all providers: {e}", exc_info=True)
        raise
