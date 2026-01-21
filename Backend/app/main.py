"""
NBA Bets Backend - FastAPI Application
Main application entry point
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
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
    user, bet, transaction,
    team, game, team_stats,
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

# Mount static files for avatars
uploads_dir = Path("Backend/uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

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
