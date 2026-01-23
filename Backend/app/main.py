"""
NBA Bets Backend - FastAPI Application
Main application entry point
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import os
import mimetypes
import re
import logging
from pathlib import Path
from dotenv import load_dotenv

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import app_engine, espn_engine, AppBase, EspnBase, sys_engine, SysBase  # sys_* son aliases para compatibilidad
from app.middleware.security_middleware import (
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    TrustedHostMiddleware
)
# Importar todos los modelos para que SQLAlchemy los registre
from app.models import (
    # Core models
    UserAccount, Client, Administrator, Operator,  # Normalized user models (replaces 'user')
    UserTwoFactor,  # Two-Factor Authentication
    UserSession,  # User sessions tracking
    Team, Game, TeamStatsGame,
    Transaction,
    # Normalized ESPN models (replaces 'bet')
    EspnBet, EspnBetType, EspnBetStatus, BetSelection, BetResult, GameOdds,
    # RBAC models
    Role, Permission, RolePermission, UserRole,
    # Idempotency and requests
    IdempotencyKey, Request,
    # Predictions
    ModelVersion, Prediction,
    # Providers
    Provider, ProviderEndpoint,
    # Snapshots
    OddsSnapshot, OddsLine,
    # Audit and messaging
    AuditLog, Outbox,
)

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="NBA Bets Prediction API",
    description="API para predicción de resultados NBA y simulación de apuestas virtuales",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - Definido directamente en el código
# Incluye URLs de desarrollo local y producción (Vercel)
cors_origins = [
    # Desarrollo local
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:4173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:4173",
    # Producción Vercel - URL principal
    "https://house-always-win.vercel.app",
    # Producción Vercel - URLs de preview/deployment específicas
    "https://house-always-win-git-main-kjsvbshks-projects.vercel.app",
]

# Regex para permitir cualquier subdominio de vercel.app (previews automáticos)
# Esto cubre todos los deployments de preview que Vercel genera automáticamente
cors_origin_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Requires-2FA"],  # Expose custom headers for 2FA flow
)

# Security Middlewares
# Order matters: HTTPS redirect first, then trusted host, then security headers
# HTTPS redirect should be early to catch HTTP requests before processing
if settings.FORCE_HTTPS:
    app.add_middleware(
        HTTPSRedirectMiddleware,
        force_https=settings.FORCE_HTTPS,
        allowed_hosts=settings.allowed_hosts_list
    )

# Trusted host validation
if settings.allowed_hosts_list:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list
    )

# Security headers (always enabled)
app.add_middleware(SecurityHeadersMiddleware)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create structured logger
structured_logger = logging.getLogger("nba_bets_api")
structured_logger.setLevel(logging.INFO)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Uploads directory (avatars). Same path as users.upload_avatar / delete_avatar.
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
avatars_dir = uploads_dir / "avatars"
uploads_dir.mkdir(parents=True, exist_ok=True)
avatars_dir.mkdir(parents=True, exist_ok=True)

# When avatar file is missing (e.g. ephemeral fs on Render), redirect to a placeholder.
# Uses ui-avatars.com; colors match app theme (background #0B132B, accent #00FF73).
_DEFAULT_AVATAR_URL = "https://ui-avatars.com/api/?name=User&size=128&background=0B132B&color=00FF73"

def _safe_avatar_filename(name: str) -> str:
    """Allow only alphanumeric, underscore, hyphen, dot (e.g. 6_1bfc18e4.png)."""
    safe = re.sub(r"[^a-zA-Z0-9_.\-]", "", name)
    return safe or "default"

@app.get("/uploads/avatars/{filename:path}")
async def serve_avatar(filename: str):
    """
    Serve user avatar by filename. If the file does not exist (e.g. ephemeral fs on Render),
    return a default placeholder so /uploads/avatars/* never 404s when the DB has a URL.
    """
    safe = _safe_avatar_filename(Path(filename).name)
    path = avatars_dir / safe
    if path.exists() and path.is_file():
        media_type, _ = mimetypes.guess_type(str(path))
        return FileResponse(path, media_type=media_type or "image/png")
    return RedirectResponse(url=_DEFAULT_AVATAR_URL, status_code=302)

# Initialize queue service (will connect to Redis if configured)
from app.services.queue_service import queue_service
if queue_service.is_available():
    print("✅ Queue service initialized (Redis + RQ)")
else:
    print("⚠️  Queue service using fallback (tasks will execute synchronously)")

# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with user-friendly messages"""
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        message = error.get("msg", "Invalid value")
        error_messages.append(f"{field}: {message}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": error_messages
        }
    )

@app.on_event("startup")
async def startup_event():
    """Initialize database tables and start background workers"""
    try:
        # IMPORTANTE: Crear primero las tablas de espn porque app tiene referencias a espn
        # Crear tablas en Neon (esquema espn)
        EspnBase.metadata.create_all(bind=espn_engine)
        print("✅ Database tables created in Neon (schema: espn)")
        
        # Crear tablas en Neon (esquema app) - después de espn
        AppBase.metadata.create_all(bind=app_engine)
        print("✅ Database tables created in Neon (schema: app)")
        
        # Iniciar worker del outbox (RF-08)
        try:
            from app.workers.outbox_worker import start_outbox_worker
            await start_outbox_worker()
            print("✅ Outbox worker started")
        except Exception as e:
            print(f"⚠️  Warning: Could not start outbox worker: {e}")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        import traceback
        traceback.print_exc()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "NBA Bets Prediction API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background workers"""
    try:
        from app.workers.outbox_worker import stop_outbox_worker
        await stop_outbox_worker()
        print("✅ Outbox worker stopped")
    except Exception as e:
        print(f"⚠️  Warning: Error stopping outbox worker: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint (legacy - use /api/v1/health/health)"""
    return {"status": "healthy", "service": "nba-bets-api"}

# Global exception handler with structured logging
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    import logging
    
    # Configure structured logging
    logger = logging.getLogger("nba_bets_api")
    logger.setLevel(logging.ERROR)
    
    # Log error with context
    error_context = {
        "path": str(request.url.path),
        "method": request.method,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc()
    }
    
    # Log to console (in production, this would go to a log aggregation service)
    logger.error(f"Unhandled exception: {error_context}")
    
    # Don't expose internal errors in production
    error_message = "Internal server error"
    if settings.DEBUG:
        error_message = f"Internal server error: {str(exc)}"
    
    return JSONResponse(
        status_code=500,
        content={"detail": error_message, "error_type": type(exc).__name__},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
