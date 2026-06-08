"""
Two-Factor Authentication service
Handles TOTP (Time-based One-Time Password) generation and verification
"""

import pyotp
import qrcode
import io
import base64
import secrets
import hashlib
import json
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models.two_factor import UserTwoFactor
from app.models.user_accounts import UserAccount

class TwoFactorService:
    def __init__(self, db: Session):
        self.db = db
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    def get_totp_uri(self, secret: str, email: str, issuer: str = "NBA Bets") -> str:
        """Generate TOTP URI for QR code"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=issuer
        )
    
    def generate_qr_code(self, uri: str) -> str:
        """Generate QR code as data URL"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Convert to base64 data URL
        img_base64 = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_base64}"
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for 2FA recovery"""
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
            codes.append(code)
        return codes
    
    def hash_backup_code(self, code: str) -> str:
        """Hash a backup code for storage"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify a TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # Allow 1 time step window
    
    def verify_backup_code(self, hashed_codes: str, code: str) -> bool:
        """Verify a backup code"""
        if not hashed_codes:
            return False
        try:
            codes_list = json.loads(hashed_codes)
            code_hash = self.hash_backup_code(code)
            return code_hash in codes_list
        except:
            return False
    
    async def get_user_2fa(self, user_id: int) -> Optional[UserTwoFactor]:
        """Get 2FA configuration for a user"""
        return self.db.query(UserTwoFactor).filter(
            UserTwoFactor.user_account_id == user_id
        ).first()
    
    async def setup_2fa(self, user_id: int, email: str) -> Tuple[str, str, List[str]]:
        """Setup 2FA for a user - returns secret, QR code URL, and backup codes"""
        # Check if 2FA already exists
        existing = await self.get_user_2fa(user_id)
        if existing and existing.is_enabled:
            raise ValueError("2FA is already enabled for this user")
        
        # Generate new secret and backup codes
        secret = self.generate_secret()
        backup_codes = self.generate_backup_codes()
        
        # Hash backup codes for storage
        hashed_codes = [self.hash_backup_code(code) for code in backup_codes]
        
        if existing:
            # Update existing record
            existing.secret = secret
            existing.backup_codes = json.dumps(hashed_codes)
            existing.is_enabled = False
        else:
            # Create new record
            two_factor = UserTwoFactor(
                user_account_id=user_id,
                secret=secret,
                backup_codes=json.dumps(hashed_codes),
                is_enabled=False
            )
            self.db.add(two_factor)
        
        self.db.commit()
        
        # Generate QR code
        uri = self.get_totp_uri(secret, email)
        qr_code_url = self.generate_qr_code(uri)
        
        return secret, qr_code_url, backup_codes
    
    async def verify_and_enable_2fa(self, user_id: int, code: str) -> bool:
        """Verify the code and enable 2FA"""
        two_factor = await self.get_user_2fa(user_id)
        if not two_factor:
            raise ValueError("2FA not set up for this user")
        
        if two_factor.is_enabled:
            raise ValueError("2FA is already enabled")
        
        # Verify the code
        if not self.verify_totp(two_factor.secret, code):
            # Also check backup codes
            if not self.verify_backup_code(two_factor.backup_codes, code):
                return False
        
        # Enable 2FA
        from datetime import datetime
        two_factor.is_enabled = True
        two_factor.enabled_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    async def disable_2fa(self, user_id: int) -> bool:
        """Disable 2FA for a user"""
        two_factor = await self.get_user_2fa(user_id)
        if not two_factor:
            return False
        
        two_factor.is_enabled = False
        two_factor.enabled_at = None
        self.db.commit()
        
        return True
    
    async def verify_2fa_code(self, user_id: int, code: str) -> bool:
        """Verify a 2FA code for login"""
        two_factor = await self.get_user_2fa(user_id)
        if not two_factor or not two_factor.is_enabled:
            return False
        
        # Try TOTP code first
        if self.verify_totp(two_factor.secret, code):
            return True
        
        # Try backup code
        if self.verify_backup_code(two_factor.backup_codes, code):
            # Remove used backup code
            codes_list = json.loads(two_factor.backup_codes)
            code_hash = self.hash_backup_code(code)
            if code_hash in codes_list:
                codes_list.remove(code_hash)
                two_factor.backup_codes = json.dumps(codes_list) if codes_list else None
                self.db.commit()
            return True
        
        return False
    
    async def is_2fa_enabled(self, user_id: int) -> bool:
        """Check if 2FA is enabled for a user"""
        two_factor = await self.get_user_2fa(user_id)
        return two_factor is not None and two_factor.is_enabled
    
    async def get_2fa_status(self, user_id: int) -> Tuple[bool, bool]:
        """Get 2FA status - returns (is_setup, is_enabled)"""
        two_factor = await self.get_user_2fa(user_id)
        if not two_factor:
            return False, False
        return True, two_factor.is_enabled
