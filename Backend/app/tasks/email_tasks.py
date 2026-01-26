"""
Email tasks for RQ
Background tasks for sending emails
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from app.services.email_service import EmailService
from app.services.cache_service import cache_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Check if SendGrid is available
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False


def send_verification_email_task(email: str, purpose: str = 'registration', expires_minutes: int = 15):
    """
    Background task to send verification email via RQ
    This function is executed by RQ worker (must be synchronous)
    
    Args:
        email: Email address to send to
        purpose: 'registration' or 'password_reset'
        expires_minutes: Minutes until code expires
    
    Returns:
        The verification code that was sent
    """
    try:
        # Generate code (synchronous)
        code = EmailService.generate_verification_code()
        
        # Store code in cache (synchronous)
        from datetime import datetime
        cache_key = f"verification_code:{email}:{purpose}"
        cache_data = {
            "code": code,
            "email": email,
            "purpose": purpose,
            "created_at": datetime.utcnow().isoformat(),
            "is_verified": False
        }
        cache_service.set(
            key=cache_key,
            data=cache_data,
            ttl_seconds=expires_minutes * 60
        )
        
        # Send email (async, but we run it in sync context)
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        
        # Handle async email sending in sync context
        # Check if we're in an async context (FastAPI) or standalone (RQ worker)
        try:
            # Try to get the running loop - this will raise RuntimeError if no loop is running
            asyncio.get_running_loop()
            # If we get here, we're inside an async context (FastAPI)
            # This shouldn't happen in RQ worker, but if called from FastAPI fallback, handle it
            # Use a separate thread with its own event loop
            import concurrent.futures
            def run_async_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    if settings.EMAIL_PROVIDER == "sendgrid":
                        new_loop.run_until_complete(EmailService._send_via_sendgrid(email, code, purpose, expires_at))
                    else:
                        # Console mode (development)
                        logger.info(f"📧 Verification code for {email} ({purpose}): {code}")
                        logger.info(f"   Expires at: {expires_at}")
                        if settings.EMAIL_PROVIDER != "console":
                            logger.warning(f"⚠️  EMAIL_PROVIDER is '{settings.EMAIL_PROVIDER}' but only 'sendgrid' is supported. Using console mode.")
                finally:
                    new_loop.close()
            
            # Run in a separate thread with its own event loop
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                future.result()  # Wait for completion
        except RuntimeError:
            # No running loop, we're in a sync context (RQ worker) - this is the normal case
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Send email via SendGrid (only supported provider)
                if settings.EMAIL_PROVIDER == "sendgrid":
                    loop.run_until_complete(
                        EmailService._send_via_sendgrid(email, code, purpose, expires_at)
                    )
                else:
                    # Console mode (development)
                    logger.info(f"📧 Verification code for {email} ({purpose}): {code}")
                    logger.info(f"   Expires at: {expires_at}")
                    if settings.EMAIL_PROVIDER != "console":
                        logger.warning(f"⚠️  EMAIL_PROVIDER is '{settings.EMAIL_PROVIDER}' but only 'sendgrid' is supported. Using console mode.")
            finally:
                loop.close()
        
        logger.info(f"✅ Verification email sent to {email} via RQ")
        return code
    except Exception as e:
        logger.error(f"❌ Error sending verification email to {email}: {e}", exc_info=True)
        raise


def send_account_deactivation_email_task(email: str, deactivated_by_admin: bool = False, admin_username: Optional[str] = None):
    """
    Background task to send account deactivation notification email
    This function is executed by RQ worker (must be synchronous)
    
    Args:
        email: Email address to send to
        deactivated_by_admin: True if deactivated by admin, False if self-deactivated
        admin_username: Username of admin who deactivated (if deactivated_by_admin is True)
    """
    try:
        from app.services.email_service import EmailService
        import asyncio
        
        # Generate email content
        if deactivated_by_admin:
            subject = "Tu cuenta ha sido desactivada por un administrador"
            admin_info = ""
            if admin_username:
                admin_info = f" por el administrador <strong>{admin_username}</strong>"
            content = f"""
                <p>Hola,</p>
                <p>Te informamos que tu cuenta en <strong>House Always Win</strong> ha sido desactivada{admin_info}.</p>
                <p>Si crees que esto es un error o necesitas más información, por favor contacta con nuestro equipo de soporte.</p>
                <p>Para reactivar tu cuenta, necesitarás contactar con un administrador del sistema.</p>
                <p>Gracias por tu comprensión.</p>
            """
        else:
            subject = "Tu cuenta ha sido desactivada"
            content = """
                <p>Hola,</p>
                <p>Te informamos que tu cuenta en <strong>House Always Win</strong> ha sido desactivada exitosamente.</p>
                <p>Gracias por haber sido parte de nuestra comunidad. Esperamos verte de nuevo pronto.</p>
                <p>Si en el futuro deseas reactivar tu cuenta, por favor contacta con un administrador del sistema.</p>
                <p>¡Que tengas un excelente día!</p>
            """
        
        # Generate full HTML email
        full_html = EmailService._get_notification_html_template(subject, content)
        
        # Send via SendGrid (only supported email provider)
        if settings.EMAIL_PROVIDER == "sendgrid":
            if not SENDGRID_AVAILABLE:
                logger.error(f"❌ SendGrid package not installed. Install with: pip install sendgrid")
                logger.info(f"📧 Account deactivation email (console mode): {email} - {subject}")
            elif not settings.SENDGRID_API_KEY or not settings.SENDGRID_FROM_EMAIL:
                logger.error(f"❌ SendGrid not configured. Missing SENDGRID_API_KEY or SENDGRID_FROM_EMAIL")
                logger.info(f"📧 Account deactivation email (console mode): {email} - {subject}")
            else:
                try:
                    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                    message = Mail(
                        from_email=settings.SENDGRID_FROM_EMAIL,
                        to_emails=email,
                        subject=subject,
                        html_content=full_html
                    )
                    response = sg.send(message)
                    if response.status_code in [200, 201, 202]:
                        logger.info(f"✅ Account deactivation email sent to {email} via SendGrid (status: {response.status_code})")
                    else:
                        logger.warning(f"⚠️  SendGrid returned status {response.status_code} for deactivation email")
                        logger.info(f"📧 Account deactivation email may not have been sent")
                except Exception as e:
                    logger.error(f"❌ Error sending deactivation email via SendGrid: {e}", exc_info=True)
                    # Fallback to console
                    logger.info(f"📧 Account deactivation email (console mode): {email} - {subject}")
        else:
            # Console mode (development or if SendGrid not configured)
            logger.info(f"📧 Account deactivation email (console mode): {email}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Content preview: {content[:100]}...")
            if settings.EMAIL_PROVIDER != "console":
                logger.warning(f"⚠️  EMAIL_PROVIDER is '{settings.EMAIL_PROVIDER}' but only 'sendgrid' is supported. Using console mode.")
        
        logger.info(f"✅ Account deactivation email processed for {email}")
    except Exception as e:
        logger.error(f"❌ Error in send_account_deactivation_email_task for {email}: {e}", exc_info=True)
        raise


def send_notification_email_task(email: str, subject: str, html_content: str):
    """
    Background task to send notification email via SendGrid
    This function is executed by RQ worker
    
    Args:
        email: Email address to send to
        subject: Email subject
        html_content: HTML content of the email
    """
    try:
        from app.services.email_service import EmailService
        import asyncio
        
        # Generate full HTML email
        full_html = EmailService._get_notification_html_template(subject, html_content)
        
        # Send via SendGrid (only supported email provider)
        if settings.EMAIL_PROVIDER == "sendgrid":
            if not SENDGRID_AVAILABLE:
                logger.error(f"❌ SendGrid package not installed. Install with: pip install sendgrid")
                logger.info(f"📧 Notification email (console mode): {email} - {subject}")
            elif not settings.SENDGRID_API_KEY or not settings.SENDGRID_FROM_EMAIL:
                logger.error(f"❌ SendGrid not configured. Missing SENDGRID_API_KEY or SENDGRID_FROM_EMAIL")
                logger.info(f"📧 Notification email (console mode): {email} - {subject}")
            else:
                try:
                    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                    message = Mail(
                        from_email=settings.SENDGRID_FROM_EMAIL,
                        to_emails=email,
                        subject=subject,
                        html_content=full_html
                    )
                    response = sg.send(message)
                    if response.status_code in [200, 201, 202]:
                        logger.info(f"✅ Notification email sent to {email} via SendGrid (status: {response.status_code})")
                    else:
                        logger.warning(f"⚠️  SendGrid returned status {response.status_code}")
                        logger.info(f"📧 Notification email may not have been sent")
                except Exception as e:
                    logger.error(f"❌ Error sending notification email via SendGrid: {e}", exc_info=True)
                    # Fallback to console
                    logger.info(f"📧 Notification email (console mode): {email} - {subject}")
        else:
            # Console mode (development or if SendGrid not configured)
            logger.info(f"📧 Notification email (console mode): {email}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Content preview: {html_content[:100]}...")
            if settings.EMAIL_PROVIDER != "console":
                logger.warning(f"⚠️  EMAIL_PROVIDER is '{settings.EMAIL_PROVIDER}' but only 'sendgrid' is supported. Using console mode.")
    except Exception as e:
        logger.error(f"❌ Error sending notification email to {email}: {e}", exc_info=True)
        # Fallback to console
        logger.info(f"📧 Notification email (console mode): {email} - {subject}")
        logger.info(f"   Content: {html_content[:100]}...")
