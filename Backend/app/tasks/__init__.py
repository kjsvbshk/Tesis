"""
Background tasks for RQ
"""

from app.tasks.email_tasks import send_verification_email_task, send_notification_email_task, send_account_deactivation_email_task
from app.tasks.provider_tasks import sync_provider_data_task, sync_all_providers_task
from app.tasks.maintenance_tasks import cleanup_expired_cache_task, cleanup_old_audit_logs_task

__all__ = [
    "send_verification_email_task",
    "send_notification_email_task",
    "send_account_deactivation_email_task",
    "sync_provider_data_task",
    "sync_all_providers_task",
    "cleanup_expired_cache_task",
    "cleanup_old_audit_logs_task",
]
