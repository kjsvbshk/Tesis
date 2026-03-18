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
        Crea o reutiliza una sesión para el dispositivo del usuario.

        Estrategia de reutilización:
        - Se busca una sesión existente del mismo usuario y tipo de dispositivo
          (device_info: "Chrome", "Firefox", etc.) que no haya sido revocada
          explícitamente, sin importar si está expirada o activa.
        - Si se encuentra, se actualiza con el nuevo token y se reactiva.
        - Si no se encuentra, se crea una fila nueva.

        Por qué NO se usa user_agent exacto para el match:
          El string de User-Agent incluye la versión del navegador
          (ej: Chrome/131.0.0.0). Con cada actualización del navegador ese
          string cambia y el match falla, generando una fila nueva por cada
          actualización aunque sea el mismo dispositivo.

        Por qué NO se usa SKIP LOCKED:
          with_for_update(skip_locked=True) devuelve None si la fila está
          bloqueada por una transacción concurrente, lo que fuerza la creación
          de una sesión duplicada innecesariamente.

        Sesiones revocadas explícitamente (revoked_at IS NOT NULL) nunca se
        reutilizan para preservar la intención de seguridad del usuario.
        """
        token_hash = self.hash_token(token)

        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Determinar el criterio de búsqueda según la información disponible.
        # Para navegadores conocidos usamos device_info (estable entre versiones).
        # Para navegadores desconocidos usamos user_agent exacto como fallback.
        existing = None
        known_browsers = {"Chrome", "Firefox", "Safari", "Edge", "Opera"}

        if device_info and device_info in known_browsers:
            existing = self.db.query(UserSession).filter(
                UserSession.user_account_id == user_id,
                UserSession.device_info == device_info,
                UserSession.revoked_at == None,
            ).order_by(UserSession.created_at.desc()).first()
        elif user_agent:
            existing = self.db.query(UserSession).filter(
                UserSession.user_account_id == user_id,
                UserSession.user_agent == user_agent,
                UserSession.revoked_at == None,
            ).order_by(UserSession.created_at.desc()).first()

        if existing:
            existing.token_hash = token_hash
            existing.ip_address = ip_address
            existing.user_agent = user_agent  # actualizar por si cambió la versión
            existing.location = location
            existing.is_active = True         # reactivar si estaba expirada
            existing.expires_at = expires_at
            existing.last_activity = now_utc
            existing.revoked_at = None
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
        now_utc = datetime.now(timezone.utc)
        query = self.db.query(UserSession).filter(
            UserSession.user_account_id == user_id
        )

        if not include_revoked:
            # Solo sesiones activas y no expiradas
            query = query.filter(
                UserSession.is_active == True,
                UserSession.expires_at > now_utc,
            )

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
