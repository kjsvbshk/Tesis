"""
Email tasks for RQ
Background tasks for sending emails
"""

import logging
import asyncio
from datetime import datetime, timedelta
from app.services.email_service import EmailService
from app.services.cache_service import cache_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Check if Resend is available
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False


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
                    if settings.EMAIL_PROVIDER == "resend":
                        new_loop.run_until_complete(EmailService._send_via_resend(email, code, purpose, expires_at))
                    elif settings.EMAIL_PROVIDER == "sendgrid":
                        new_loop.run_until_complete(EmailService._send_via_sendgrid(email, code, purpose, expires_at))
                    elif settings.EMAIL_PROVIDER == "smtp":
                        new_loop.run_until_complete(EmailService._send_via_smtp(email, code, purpose, expires_at))
                    else:
                        # Console mode
                        logger.info(f"📧 Verification code for {email} ({purpose}): {code}")
                        logger.info(f"   Expires at: {expires_at}")
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
                # Send email based on provider
                if settings.EMAIL_PROVIDER == "resend":
                    loop.run_until_complete(
                        EmailService._send_via_resend(email, code, purpose, expires_at)
                    )
                elif settings.EMAIL_PROVIDER == "sendgrid":
                    loop.run_until_complete(
                        EmailService._send_via_sendgrid(email, code, purpose, expires_at)
                    )
                elif settings.EMAIL_PROVIDER == "smtp":
                    loop.run_until_complete(
                        EmailService._send_via_smtp(email, code, purpose, expires_at)
                    )
                else:
                    # Console mode
                    logger.info(f"📧 Verification code for {email} ({purpose}): {code}")
                    logger.info(f"   Expires at: {expires_at}")
            finally:
                loop.close()
        
        logger.info(f"✅ Verification email sent to {email} via RQ")
        return code
    except Exception as e:
        logger.error(f"❌ Error sending verification email to {email}: {e}", exc_info=True)
        raise


def send_notification_email_task(email: str, subject: str, html_content: str):
    """
    Background task to send notification email
    This function is executed by RQ worker
    
    Args:
        email: Email address to send to
        subject: Email subject
        html_content: HTML content of the email
    """
    try:
        from app.services.email_service import EmailService
        import asyncio
        
        email_service = EmailService()
        
        # Send email via Resend (async function in sync context)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if settings.EMAIL_PROVIDER == "resend" and RESEND_AVAILABLE and settings.RESEND_API_KEY:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            
            # Ensure 'from' format is correct
            from_email = settings.RESEND_FROM_EMAIL
            if "<" not in from_email and ">" not in from_email:
                from_email = f"House Always Win <{from_email}>"
            
            # Generate full HTML email
            full_html = EmailService._get_notification_html_template(subject, html_content)
            
            response = resend.Emails.send({
                "from": from_email,
                "to": [email],  # Use list format for consistency
                "subject": subject,
                "html": full_html
            })
            
            if response and isinstance(response, dict) and response.get('id'):
                logger.info(f"✅ Notification email sent to {email} via RQ (ID: {response.get('id')})")
            else:
                error = response.get('error') if isinstance(response, dict) else "Unknown error"
                logger.warning(f"⚠️  Notification email may not have been sent to {email}: {error}")
                logger.debug(f"   Resend response: {response}")
        else:
            # Console mode or fallback
            logger.info(f"📧 Notification email (console mode): {email} - {subject}")
            logger.info(f"   Content: {html_content[:100]}...")
    except Exception as e:
        logger.error(f"❌ Error sending notification email to {email}: {e}", exc_info=True)
        raise
