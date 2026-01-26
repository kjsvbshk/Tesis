"""
Email service for sending verification codes
Supports SendGrid (production), SMTP (local only), and console (development) modes
"""
import random
import string
import os
from datetime import datetime, timedelta
from typing import Optional
from app.services.cache_service import cache_service
from app.core.config import settings

# Try to import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

# Try to import SMTP
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False

class EmailService:
    """Service for sending emails with multiple provider support"""
    
    @staticmethod
    def generate_verification_code() -> str:
        """Generate a 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    async def send_verification_code(
        email: str,
        purpose: str = 'registration',
        expires_minutes: int = 15
    ) -> str:
        """
        Send verification code to email
        Stores code in memory cache (not database)
        Returns the code (in production, this would send via email service)
        
        Args:
            email: Email address to send code to
            purpose: 'registration' or 'password_reset'
            expires_minutes: Minutes until code expires (default 15)
        
        Returns:
            The verification code (for development/testing)
        """
        # Generate code
        code = EmailService.generate_verification_code()
        
        # Store code in memory cache with TTL
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
        
        # Send email based on configured provider (prioritize SendGrid)
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        
        if settings.EMAIL_PROVIDER == "sendgrid":
            await EmailService._send_via_sendgrid(email, code, purpose, expires_at)
        elif settings.EMAIL_PROVIDER == "smtp":
            await EmailService._send_via_smtp(email, code, purpose, expires_at)
        else:
            # Console mode (development)
            print(f"📧 Verification code for {email} ({purpose}): {code}")
            print(f"   Expires at: {expires_at}")
            if settings.EMAIL_PROVIDER != "console":
                print(f"   ⚠️  Email provider '{settings.EMAIL_PROVIDER}' not configured, using console mode")
        
        return code
    
    @staticmethod
    def _get_notification_html_template(subject: str, content: str) -> str:
        """Generate professional HTML email template for notifications"""
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 20px; text-align: center; background: linear-gradient(135deg, #0B132B 0%, #1C2541 100%); border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #00FF73; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                                House Always Win
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin: 0 0 20px; color: #1a1a1a; font-size: 24px; font-weight: 600;">
                                {subject}
                            </h2>
                            
                            <div style="color: #4a4a4a; font-size: 16px; line-height: 1.6;">
                                {content}
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 40px; text-align: center; background-color: #f9f9f9; border-radius: 0 0 8px 8px; border-top: 1px solid #e0e0e0;">
                            <p style="margin: 0 0 8px; color: #999999; font-size: 12px; line-height: 1.5;">
                                Este es un mensaje automático, por favor no respondas a este correo.
                            </p>
                            <p style="margin: 0; color: #999999; font-size: 12px; line-height: 1.5;">
                                © {datetime.utcnow().year} House Always Win. Todos los derechos reservados.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
    
    @staticmethod
    def _get_email_html_template(code: str, purpose: str, expires_at: datetime) -> str:
        """Generate professional HTML email template"""
        purpose_text = "registro" if purpose == "registration" else "restablecimiento de contraseña"
        purpose_title = "Registro de Cuenta" if purpose == "registration" else "Restablecimiento de Contraseña"
        
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Código de Verificación</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 20px; text-align: center; background: linear-gradient(135deg, #0B132B 0%, #1C2541 100%); border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #00FF73; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                                House Always Win
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin: 0 0 20px; color: #1a1a1a; font-size: 24px; font-weight: 600;">
                                Código de Verificación
                            </h2>
                            
                            <p style="margin: 0 0 24px; color: #4a4a4a; font-size: 16px; line-height: 1.6;">
                                Hola,
                            </p>
                            
                            <p style="margin: 0 0 32px; color: #4a4a4a; font-size: 16px; line-height: 1.6;">
                                Has solicitado un código de verificación para el <strong>{purpose_text}</strong> en House Always Win. 
                                Utiliza el siguiente código para completar el proceso:
                            </p>
                            
                            <!-- Code Box -->
                            <table role="presentation" style="width: 100%; margin: 32px 0;">
                                <tr>
                                    <td align="center" style="padding: 24px; background: linear-gradient(135deg, #0B132B 0%, #1C2541 100%); border-radius: 8px; border: 2px solid #00FF73;">
                                        <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #00FF73; font-family: 'Courier New', monospace;">
                                            {code}
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 24px 0 0; color: #666666; font-size: 14px; line-height: 1.5;">
                                <strong>⏰ Este código expira el:</strong><br>
                                {expires_at.strftime('%d de %B de %Y a las %H:%M')} UTC
                            </p>
                            
                            <p style="margin: 32px 0 0; color: #666666; font-size: 14px; line-height: 1.6;">
                                Si no solicitaste este código, puedes ignorar este mensaje de forma segura. 
                                Tu cuenta permanecerá sin cambios.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 40px; text-align: center; background-color: #f9f9f9; border-radius: 0 0 8px 8px; border-top: 1px solid #e0e0e0;">
                            <p style="margin: 0 0 8px; color: #999999; font-size: 12px; line-height: 1.5;">
                                Este es un mensaje automático, por favor no respondas a este correo.
                            </p>
                            <p style="margin: 0; color: #999999; font-size: 12px; line-height: 1.5;">
                                © {datetime.utcnow().year} House Always Win. Todos los derechos reservados.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
    
    @staticmethod
    async def _send_via_sendgrid(email: str, code: str, purpose: str, expires_at: datetime):
        """Send email via SendGrid (Recommended for Render/production)"""
        if not SENDGRID_AVAILABLE:
            print(f"⚠️  SendGrid not available (package not installed), falling back to console")
            return
        
        if not settings.SENDGRID_API_KEY or not settings.SENDGRID_FROM_EMAIL:
            print(f"⚠️  SendGrid API key or from email not configured, falling back to console")
            return
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            
            purpose_text = "registro" if purpose == "registration" else "restablecimiento de contraseña"
            subject = f"Código de Verificación - {purpose_text.capitalize()}"
            
            # Use professional HTML template
            html_content = EmailService._get_email_html_template(code, purpose, expires_at)
            
            # Generate plain text content
            text_content = f"""Código de Verificación - {purpose_text.capitalize()}

Hola,

Has solicitado un código de verificación para el {purpose_text} en House Always Win.

Tu código de verificación es: {code}

Este código expira el: {expires_at.strftime('%d de %B de %Y a las %H:%M')} UTC

Si no solicitaste este código, puedes ignorar este mensaje de forma segura."""
            
            message = Mail(
                from_email=settings.SENDGRID_FROM_EMAIL,
                to_emails=email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )
            
            response = sg.send(message)
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ Email sent via SendGrid to {email} (status: {response.status_code})")
                print(f"✅ Email sent via SendGrid to {email}")
            else:
                logger.warning(f"⚠️  SendGrid returned status {response.status_code}, email may not have been sent")
                print(f"⚠️  SendGrid returned status {response.status_code}, email may not have been sent")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error sending email via SendGrid: {e}", exc_info=True)
            print(f"❌ Error sending email via SendGrid: {e}")
            print(f"   Falling back to console mode")
    
    @staticmethod
    async def _send_via_smtp(email: str, code: str, purpose: str, expires_at: datetime):
        """Send email via SMTP (Gmail - Only works locally, NOT on Render)"""
        if not SMTP_AVAILABLE:
            print(f"⚠️  SMTP not available, falling back to console")
            return
        
        # Use SMTP_FROM_EMAIL if set, otherwise use SMTP_USER
        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        
        if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD]):
            print(f"⚠️  SMTP configuration incomplete (missing SMTP_USER or SMTP_PASSWORD), falling back to console")
            return
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            purpose_text = "registro" if purpose == "registration" else "restablecimiento de contraseña"
            subject = f"Código de Verificación - {purpose_text.capitalize()}"
            
            # Use professional HTML template
            html_content = EmailService._get_email_html_template(code, purpose, expires_at)
            
            # Generate plain text content
            text_content = f"""Código de Verificación - {purpose_text.capitalize()}

Hola,

Has solicitado un código de verificación para el {purpose_text} en House Always Win.

Tu código de verificación es: {code}

Este código expira el: {expires_at.strftime('%d de %B de %Y a las %H:%M')} UTC

Si no solicitaste este código, puedes ignorar este mensaje de forma segura."""
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = email
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Gmail: Try port 587 with STARTTLS first (works better on Render/cloud), fallback to 465 with SSL
            timeout_seconds = 30
            port = settings.SMTP_PORT
            
            # If port is 465, use SMTP_SSL. If 587, use SMTP with STARTTLS
            if port == 465:
                # Gmail uses SMTP_SSL on port 465
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, port, timeout=timeout_seconds)
            elif port == 587:
                # Gmail uses STARTTLS on port 587 (better for cloud platforms like Render)
                server = smtplib.SMTP(settings.SMTP_HOST, port, timeout=timeout_seconds)
                server.starttls()
            else:
                # Default to STARTTLS for other ports
                server = smtplib.SMTP(settings.SMTP_HOST, port, timeout=timeout_seconds)
                if settings.SMTP_USE_TLS:
                    server.starttls()
            
            try:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(from_email, email, msg.as_string())
                logger.info(f"✅ Email sent via SMTP (Gmail) to {email}")
                print(f"✅ Email sent via SMTP (Gmail) to {email}")
            finally:
                server.close()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error sending email via SMTP: {e}", exc_info=True)
            print(f"❌ Error sending email via SMTP: {e}")
            print(f"   Falling back to console mode")
    
    @staticmethod
    async def verify_code(
        email: str,
        code: str,
        purpose: str
    ) -> bool:
        """
        Verify the code and mark as verified
        Checks code in memory cache (not database)
        
        Args:
            email: Email address
            code: Verification code to check
            purpose: 'registration' or 'password_reset'
        
        Returns:
            True if code is valid and verified, False otherwise
        """
        cache_key = f"verification_code:{email}:{purpose}"
        cached = cache_service.get(cache_key, allow_stale=False)
        
        if not cached or not cached.get("data"):
            return False
        
        verification_data = cached["data"]
        
        # Check if code matches
        if verification_data.get("code") != code:
            return False
        
        # If already verified, return True (allow re-verification for password reset flow)
        if verification_data.get("is_verified", False):
            return True
        
        # Mark as verified and update cache
        verification_data["is_verified"] = True
        verification_data["verified_at"] = datetime.utcnow().isoformat()
        
        # Update cache with verified status (extend TTL for verified codes)
        cache_service.set(
            key=cache_key,
            data=verification_data,
            ttl_seconds=30 * 60  # 30 minutes for verified codes
        )
        
        return True
    
    @staticmethod
    async def is_code_verified(
        email: str,
        purpose: str
    ) -> bool:
        """
        Check if code has been verified for this email and purpose
        Checks in memory cache (not database)
        
        Args:
            email: Email address
            purpose: 'registration' or 'password_reset'
        
        Returns:
            True if a verified code exists, False otherwise
        """
        cache_key = f"verification_code:{email}:{purpose}"
        cached = cache_service.get(cache_key, allow_stale=False)
        
        if not cached or not cached.get("data"):
            return False
        
        verification_data = cached["data"]
        
        # Check if code is verified
        if not verification_data.get("is_verified", False):
            return False
        
        # Check if verification is still valid (within last 30 minutes for registration, 15 for password reset)
        verified_at_str = verification_data.get("verified_at")
        if not verified_at_str:
            return False
        
        verified_at = datetime.fromisoformat(verified_at_str.replace('Z', '+00:00'))
        valid_duration = timedelta(minutes=30) if purpose == 'registration' else timedelta(minutes=15)
        
        if (datetime.utcnow() - verified_at.replace(tzinfo=None)) > valid_duration:
            return False
        
        return True
    
    @staticmethod
    async def send_account_deactivation_notification(
        email: str,
        deactivated_by_admin: bool = False,
        admin_username: Optional[str] = None
    ):
        """
        Send account deactivation notification email
        
        Args:
            email: Email address to send notification to
            deactivated_by_admin: True if deactivated by admin, False if self-deactivated
            admin_username: Username of admin who deactivated (if deactivated_by_admin is True)
        """
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
        
        html_content = EmailService._get_notification_html_template(subject, content)
        
        # Send email based on configured provider
        if settings.EMAIL_PROVIDER == "sendgrid":
            await EmailService._send_notification_via_sendgrid(email, subject, html_content)
        elif settings.EMAIL_PROVIDER == "smtp":
            await EmailService._send_notification_via_smtp(email, subject, html_content)
        else:
            # Console mode (development)
            print(f"📧 Account deactivation notification to {email}")
            print(f"   Subject: {subject}")
            if settings.EMAIL_PROVIDER != "console":
                print(f"   ⚠️  Email provider '{settings.EMAIL_PROVIDER}' not configured, using console mode")
    
    @staticmethod
    def _send_notification_via_sendgrid_sync(email: str, subject: str, html_content: str):
        """Send notification email via SendGrid (synchronous, to be run in thread pool)"""
        if not SENDGRID_AVAILABLE:
            print(f"⚠️  SendGrid not available, falling back to console")
            return
        
        if not settings.SENDGRID_API_KEY or not settings.SENDGRID_FROM_EMAIL:
            print(f"⚠️  SendGrid API key or from email not configured, falling back to console")
            return
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            message = Mail(
                from_email=settings.SENDGRID_FROM_EMAIL,
                to_emails=email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"✅ Notification email sent via SendGrid to {email} (status: {response.status_code})")
                print(f"✅ Notification email sent via SendGrid to {email}")
            else:
                logger.warning(f"⚠️  SendGrid returned status {response.status_code}, email may not have been sent")
                print(f"⚠️  SendGrid returned status {response.status_code}, email may not have been sent")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error sending notification email via SendGrid: {e}", exc_info=True)
            print(f"❌ Error sending notification email via SendGrid: {e}")
    
    @staticmethod
    async def _send_notification_via_sendgrid(email: str, subject: str, html_content: str):
        """Send notification email via SendGrid (async wrapper)"""
        import asyncio
        # Run blocking I/O in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            EmailService._send_notification_via_sendgrid_sync,
            email,
            subject,
            html_content
        )
    
    @staticmethod
    def _send_notification_via_smtp_sync(email: str, subject: str, html_content: str):
        """Send notification email via SMTP (synchronous, to be run in thread pool)"""
        if not SMTP_AVAILABLE:
            print(f"⚠️  SMTP not available, falling back to console")
            return
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            from_email = settings.SMTP_FROM_EMAIL or settings.SENDGRID_FROM_EMAIL
            smtp_host = settings.SMTP_HOST or "smtp.gmail.com"
            smtp_port = settings.SMTP_PORT or 587
            smtp_user = settings.SMTP_USER
            smtp_password = settings.SMTP_PASSWORD
            
            if not from_email or not smtp_user or not smtp_password:
                print(f"⚠️  SMTP credentials not configured, falling back to console")
                return
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = email
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Use same logic as _send_via_smtp for port handling
            timeout_seconds = 30
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout_seconds)
            elif smtp_port == 587:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout_seconds)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout_seconds)
                if getattr(settings, 'SMTP_USE_TLS', True):
                    server.starttls()
            
            try:
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, email, msg.as_string())
                logger.info(f"✅ Notification email sent via SMTP to {email}")
                print(f"✅ Notification email sent via SMTP to {email}")
            finally:
                server.quit()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error sending notification email via SMTP: {e}", exc_info=True)
            print(f"❌ Error sending notification email via SMTP: {e}")
            print(f"   Falling back to console mode")
    
    @staticmethod
    async def _send_notification_via_smtp(email: str, subject: str, html_content: str):
        """Send notification email via SMTP (async wrapper)"""
        import asyncio
        # Run blocking I/O in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            EmailService._send_notification_via_smtp_sync,
            email,
            subject,
            html_content
        )
