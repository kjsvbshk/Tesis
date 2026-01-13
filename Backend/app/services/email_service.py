"""
Email service for sending verification codes
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional
from app.services.cache_service import cache_service

class EmailService:
    """Service for sending emails (mock implementation)"""
    
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
        
        # In production, send email here using SMTP or email service (SendGrid, AWS SES, etc.)
        # For now, print to console (in development)
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        print(f"📧 Verification code for {email} ({purpose}): {code}")
        print(f"   Expires at: {expires_at}")
        print(f"   ⚠️  In production, this would be sent via email")
        
        return code
    
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
