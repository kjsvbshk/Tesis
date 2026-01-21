"""
Security monitoring middleware for tracking failed login attempts and rate limiting
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SecurityMonitoring:
    """
    Tracks failed login attempts and implements rate limiting.
    """
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15, block_duration_minutes: int = 30):
        """
        Initialize security monitoring.
        
        Args:
            max_attempts: Maximum failed attempts before blocking
            window_minutes: Time window in minutes for tracking attempts
            block_duration_minutes: Duration to block IP after max attempts
        """
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.block_duration_minutes = block_duration_minutes
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}
    
    def track_failed_login(self, username: str, ip_address: str) -> bool:
        """
        Track a failed login attempt.
        
        Args:
            username: Username that failed to login
            ip_address: IP address of the request
        
        Returns:
            True if IP should be blocked, False otherwise
        """
        now = datetime.utcnow()
        
        # Clean old attempts for this IP
        self._clean_old_attempts(ip_address, now)
        
        # Add new failed attempt
        self.failed_attempts[ip_address].append(now)
        
        # Check if IP should be blocked
        attempts_count = len(self.failed_attempts[ip_address])
        
        if attempts_count >= self.max_attempts:
            # Block IP
            self.blocked_ips[ip_address] = now
            logger.warning(
                f"IP {ip_address} blocked due to {attempts_count} failed login attempts "
                f"for user '{username}'"
            )
            return True
        
        # Log warning if approaching limit
        if attempts_count >= self.max_attempts - 1:
            logger.warning(
                f"IP {ip_address} has {attempts_count} failed login attempts "
                f"for user '{username}' (limit: {self.max_attempts})"
            )
        else:
            logger.info(
                f"Failed login attempt for user '{username}' from IP {ip_address} "
                f"({attempts_count}/{self.max_attempts} attempts)"
            )
        
        return False
    
    def check_rate_limit(self, ip_address: str) -> Tuple[bool, Optional[int]]:
        """
        Check if an IP address is rate limited.
        
        Args:
            ip_address: IP address to check
        
        Returns:
            Tuple of (is_blocked, remaining_minutes)
        """
        if ip_address not in self.blocked_ips:
            return False, None
        
        block_time = self.blocked_ips[ip_address]
        now = datetime.utcnow()
        elapsed = now - block_time
        
        if elapsed >= timedelta(minutes=self.block_duration_minutes):
            # Unblock IP
            del self.blocked_ips[ip_address]
            # Also clear failed attempts
            if ip_address in self.failed_attempts:
                del self.failed_attempts[ip_address]
            return False, None
        
        remaining_minutes = self.block_duration_minutes - int(elapsed.total_seconds() / 60)
        return True, remaining_minutes
    
    def get_failed_attempts_count(self, ip_address: str) -> int:
        """
        Get the number of failed attempts for an IP address.
        
        Args:
            ip_address: IP address to check
        
        Returns:
            Number of failed attempts in the current window
        """
        now = datetime.utcnow()
        self._clean_old_attempts(ip_address, now)
        return len(self.failed_attempts[ip_address])
    
    def reset_attempts(self, ip_address: str):
        """
        Reset failed attempts for an IP address (e.g., after successful login).
        
        Args:
            ip_address: IP address to reset
        """
        if ip_address in self.failed_attempts:
            del self.failed_attempts[ip_address]
        if ip_address in self.blocked_ips:
            del self.blocked_ips[ip_address]
        logger.info(f"Reset failed login attempts for IP {ip_address}")
    
    def _clean_old_attempts(self, ip_address: str, now: datetime):
        """Remove attempts older than the time window."""
        if ip_address not in self.failed_attempts:
            return
        
        cutoff_time = now - timedelta(minutes=self.window_minutes)
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address]
            if attempt > cutoff_time
        ]
    
    def get_blocked_ips(self) -> Dict[str, datetime]:
        """
        Get all currently blocked IPs.
        
        Returns:
            Dictionary mapping IP addresses to block timestamps
        """
        # Clean expired blocks
        now = datetime.utcnow()
        expired_ips = [
            ip for ip, block_time in self.blocked_ips.items()
            if now - block_time >= timedelta(minutes=self.block_duration_minutes)
        ]
        for ip in expired_ips:
            del self.blocked_ips[ip]
            if ip in self.failed_attempts:
                del self.failed_attempts[ip]
        
        return self.blocked_ips.copy()


# Global instance - initialized lazily to read from settings
_security_monitoring_instance: Optional[SecurityMonitoring] = None


def get_security_monitoring() -> SecurityMonitoring:
    """
    Get or create the global security monitoring instance.
    Reads configuration from settings on first access.
    """
    global _security_monitoring_instance
    
    if _security_monitoring_instance is None:
        # Import here to avoid circular imports
        from app.core.config import settings
        
        _security_monitoring_instance = SecurityMonitoring(
            max_attempts=settings.SECURITY_MAX_LOGIN_ATTEMPTS,
            window_minutes=settings.SECURITY_LOGIN_WINDOW_MINUTES,
            block_duration_minutes=settings.SECURITY_BLOCK_DURATION_MINUTES
        )
        logger.info(
            f"Security monitoring initialized: "
            f"max_attempts={settings.SECURITY_MAX_LOGIN_ATTEMPTS}, "
            f"window_minutes={settings.SECURITY_LOGIN_WINDOW_MINUTES}, "
            f"block_duration_minutes={settings.SECURITY_BLOCK_DURATION_MINUTES}"
        )
    
    return _security_monitoring_instance


# For backward compatibility - use getter function
class _SecurityMonitoringProxy:
    """Proxy to access security_monitoring instance lazily"""
    def __getattr__(self, name):
        return getattr(get_security_monitoring(), name)


security_monitoring = _SecurityMonitoringProxy()
