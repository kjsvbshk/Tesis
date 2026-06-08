"""
Maintenance tasks for RQ
Background tasks for system maintenance
"""

import logging
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


def cleanup_expired_cache_task():
    """
    Background task to clean up expired cache entries
    This function is executed by RQ worker
    """
    try:
        count = cache_service.cleanup_expired()
        logger.info(f"✅ Cleaned up {count} expired cache entries")
        return {"cleaned": count}
    except Exception as e:
        logger.error(f"❌ Error cleaning cache: {e}", exc_info=True)
        raise


def cleanup_old_audit_logs_task(days_to_keep: int = 90):
    """
    Background task to clean up old audit logs
    This function is executed by RQ worker
    
    Args:
        days_to_keep: Number of days of logs to keep (default 90)
    """
    try:
        from sqlalchemy.orm import Session
        from app.core.database import SysSessionLocal
        from app.models import AuditLog
        from datetime import datetime, timedelta
        
        db = SysSessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old audit logs
            deleted = db.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).delete()
            
            db.commit()
            logger.info(f"✅ Cleaned up {deleted} old audit logs (older than {days_to_keep} days)")
            return {"deleted": deleted}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Error cleaning audit logs: {e}", exc_info=True)
        raise
