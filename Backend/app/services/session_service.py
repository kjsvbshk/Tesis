"""
User Session service
Handles tracking and management of active JWT sessions
"""

import hashlib
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.user_session import UserSession
from app.models.user_accounts import UserAccount
from app.core.config import settings

class SessionService:
    def __init__(self, db: Session):
        self.db = db
    
    def hash_token(self, token: str) -> str:
        """Hash a JWT token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def create_session(
        self,
        user_id: int,
        token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        location: Optional[str] = None
    ) -> UserSession:
        """
        Create a session record.

        Current behavior: if the same user logs in again from the same browser/device
        (same `user_agent` + `device_info`) and there is an active session, we update
        that existing row instead of creating a new one. This avoids duplicates in
        \"Sesiones Activas\" for the same device.
        """
        token_hash = self.hash_token(token)
        
        # Calculate expiration time
        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Reuse existing active session for same device (best-effort).
        # NOTE:
        # - IP is NOT reliable (can change), so we key primarily by user_agent/device_info.
        # - If User-Agent is missing, we DO NOT reuse sessions because multiple different
        #   clients could share device_info="Unknown" and user_agent=None, causing collisions.
        # - Bug 1 fix: Use row-level locking with SKIP LOCKED to prevent race conditions.
        #   If a session is locked by another concurrent request, skip it and create a new one.
        #   This ensures both requests get valid tokens instead of one overwriting the other.
        # - Bug 2 fix: Only reuse sessions that are not expired (expires_at > now_utc).
        existing = None
        if user_agent:
            q = self.db.query(UserSession).filter(
                UserSession.user_account_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > now_utc,  # Bug 2: Don't reuse expired sessions
            )
            # Require an exact match on both user_agent and device_info.
            q = q.filter(UserSession.user_agent == user_agent)
            q = q.filter(UserSession.device_info == device_info)
            # Bug 1: Lock with SKIP LOCKED - if row is locked by concurrent request,
            # skip it (returns None) and we'll create a new session instead.
            # This prevents the second request from overwriting the first request's token.
            existing = q.order_by(UserSession.created_at.desc()).with_for_update(skip_locked=True).first()

        if existing:
            existing.token_hash = token_hash
            existing.ip_address = ip_address
            existing.location = location
            existing.expires_at = expires_at
            existing.last_activity = now_utc
            self.db.commit()
            self.db.refresh(existing)
            return existing

        session = UserSession(
            user_account_id=user_id,
            token_hash=token_hash,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            location=location,
            is_active=True,
            expires_at=expires_at,
            last_activity=now_utc
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session
    
    async def get_session_by_token(self, token: str) -> Optional[UserSession]:
        """Get session by token hash"""
        token_hash = self.hash_token(token)
        return self.db.query(UserSession).filter(
            UserSession.token_hash == token_hash,
            UserSession.is_active == True
        ).first()
    
    async def get_user_sessions(self, user_id: int, include_revoked: bool = False) -> List[UserSession]:
        """Get all sessions for a user"""
        query = self.db.query(UserSession).filter(
            UserSession.user_account_id == user_id
        )
        
        if not include_revoked:
            query = query.filter(UserSession.is_active == True)
        
        return query.order_by(UserSession.created_at.desc()).all()
    
    async def revoke_session(self, session_id: int, user_id: int) -> bool:
        """Revoke a specific session"""
        session = self.db.query(UserSession).filter(
            UserSession.id == session_id,
            UserSession.user_account_id == user_id
        ).first()
        
        if not session:
            return False
        
        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
        self.db.commit()
        
        return True
    
    async def revoke_all_sessions(self, user_id: int, exclude_token: Optional[str] = None) -> int:
        """Revoke all sessions for a user, optionally excluding one token"""
        sessions = await self.get_user_sessions(user_id, include_revoked=False)
        
        exclude_hash = None
        if exclude_token:
            exclude_hash = self.hash_token(exclude_token)
        
        revoked_count = 0
        for session in sessions:
            if exclude_hash and session.token_hash == exclude_hash:
                continue
            
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)
            revoked_count += 1
        
        self.db.commit()
        return revoked_count
    
    async def update_session_activity(self, token: str) -> bool:
        """Update last activity time for a session"""
        session = await self.get_session_by_token(token)
        if not session:
            return False
        
        session.last_activity = datetime.now(timezone.utc)
        self.db.commit()
        
        return True
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions (optional cleanup task)"""
        expired_sessions = self.db.query(UserSession).filter(
            UserSession.expires_at < datetime.now(timezone.utc),
            UserSession.is_active == True
        ).all()
        
        count = len(expired_sessions)
        for session in expired_sessions:
            session.is_active = False
        
        self.db.commit()
        return count
    
    def extract_device_info(self, user_agent: Optional[str]) -> str:
        """Extract device/browser info from user agent"""
        if not user_agent:
            return "Unknown"
        
        # Simple extraction - can be enhanced with user_agent library
        user_agent_lower = user_agent.lower()
        
        if 'chrome' in user_agent_lower and 'edg' not in user_agent_lower:
            return "Chrome"
        elif 'firefox' in user_agent_lower:
            return "Firefox"
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            return "Safari"
        elif 'edg' in user_agent_lower:
            return "Edge"
        elif 'opera' in user_agent_lower:
            return "Opera"
        else:
            return "Unknown Browser"
