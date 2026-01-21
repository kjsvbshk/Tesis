"""
Security middleware for HTTPS enforcement and security headers
"""

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce HTTPS in production.
    Redirects HTTP requests to HTTPS (except for localhost).
    """
    
    def __init__(self, app: ASGIApp, force_https: bool = True, allowed_hosts: List[str] = None):
        super().__init__(app)
        self.force_https = force_https
        self.allowed_hosts = allowed_hosts or []
    
    async def dispatch(self, request: Request, call_next):
        # Skip HTTPS enforcement for localhost/127.0.0.1 (development)
        client_host = request.client.host if request.client else None
        is_localhost = client_host in ("127.0.0.1", "localhost") or client_host is None
        
        # Skip if HTTPS enforcement is disabled
        if not self.force_https or is_localhost:
            return await call_next(request)
        
        # Check if request is already HTTPS
        if request.url.scheme == "https":
            return await call_next(request)
        
        # Validate host if allowed_hosts is configured
        if self.allowed_hosts:
            host = request.headers.get("host", "")
            if not any(
                allowed_host in host or host.endswith(f".{allowed_host}")
                for allowed_host in self.allowed_hosts
            ):
                logger.warning(f"Request from unauthorized host: {host}")
                return Response(
                    content="Forbidden: Host not allowed",
                    status_code=403
                )
        
        # Redirect HTTP to HTTPS
        https_url = request.url.replace(scheme="https")
        logger.info(f"Redirecting HTTP to HTTPS: {request.url} -> {https_url}")
        return RedirectResponse(url=str(https_url), status_code=301)


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate trusted hosts.
    """
    
    def __init__(self, app: ASGIApp, allowed_hosts: List[str] = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or []
    
    async def dispatch(self, request: Request, call_next):
        # Skip validation if no allowed hosts configured
        if not self.allowed_hosts:
            return await call_next(request)
        
        # Skip validation for localhost
        client_host = request.client.host if request.client else None
        is_localhost = client_host in ("127.0.0.1", "localhost") or client_host is None
        
        if is_localhost:
            return await call_next(request)
        
        # Validate host header
        host = request.headers.get("host", "")
        if not host:
            logger.warning("Request missing Host header")
            return Response(
                content="Bad Request: Missing Host header",
                status_code=400
            )
        
        # Check if host is allowed
        host_allowed = any(
            allowed_host == host or host.endswith(f".{allowed_host}")
            for allowed_host in self.allowed_hosts
        )
        
        if not host_allowed:
            logger.warning(f"Request from unauthorized host: {host}")
            return Response(
                content="Forbidden: Host not allowed",
                status_code=403
            )
        
        return await call_next(request)
