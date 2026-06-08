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
        
        # Validar que el modelo ML activo tiene su .joblib en disco
        try:
            import os
            from app.core.config import settings
            from app.models import ModelVersion
            from app.core.database import get_sys_db

            db = next(get_sys_db())
            active_mv = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
            db.close()

            if active_mv:
                model_dir = settings.MODEL_DIR
                if not os.path.isabs(model_dir):
                    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    model_dir = os.path.normpath(os.path.join(backend_root, model_dir))

                joblib_path = os.path.join(model_dir, f"nba_prediction_model_{active_mv.version}.joblib")
                fallback_path = os.path.join(model_dir, "nba_prediction_model.joblib")

                if os.path.exists(joblib_path):
                    print(f"✅ Modelo ML v{active_mv.version} encontrado en disco: {joblib_path}")
                elif os.path.exists(fallback_path):
                    print(f"✅ Modelo ML encontrado (fallback genérico): {fallback_path}")
                else:
                    available = os.listdir(model_dir) if os.path.isdir(model_dir) else []
                    print(f"⚠️  ADVERTENCIA: modelo activo '{active_mv.version}' no tiene .joblib en {model_dir}")
                    print(f"⚠️  Archivos .joblib disponibles: {[f for f in available if f.endswith('.joblib')]}")
                    print(f"⚠️  Las predicciones retornarán 503 hasta que se suba el archivo.")
                    print(f"⚠️  Para generar el modelo, ejecutar localmente:")
                    print(f"⚠️    cd ML && python -m src.training.train --version {active_mv.version} --model ensemble --use-v3")
                    print(f"⚠️    git add -f ML/models/nba_prediction_model_{active_mv.version}.joblib && git push")
            else:
                print("⚠️  No hay versión de modelo activa en app.model_versions.")
        except Exception as mv_e:
            print(f"⚠️  No se pudo validar el modelo ML en startup: {mv_e}")

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

@app.get("/debug/model")
async def debug_model():
    """Diagnóstico sin auth — retorna el estado real del modelo ML en este servidor.
    SOLO para debugging; quitar en producción final."""
    import sys, traceback as tb
    from app.core.config import settings

    result: dict = {}

    # 1. Resolver MODEL_DIR
    model_dir = settings.MODEL_DIR
    if not os.path.isabs(model_dir):
        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_dir = os.path.normpath(os.path.join(backend_root, model_dir))
    result["model_dir"] = model_dir
    result["model_dir_exists"] = os.path.isdir(model_dir)
    result["model_dir_files"] = os.listdir(model_dir) if os.path.isdir(model_dir) else []

    # 2. Versión activa en DB
    try:
        from app.core.database import get_sys_db
        from app.models import ModelVersion
        db = next(get_sys_db())
        mv = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        db.close()
        result["active_version"] = mv.version if mv else None
        result["joblib_expected"] = os.path.join(model_dir, f"nba_prediction_model_{mv.version}.joblib") if mv else None
        result["joblib_exists"] = os.path.exists(result["joblib_expected"]) if result["joblib_expected"] else False
    except Exception as e:
        result["db_error"] = str(e)

    # 3. Intentar cargar el modelo
    try:
        import joblib
        path = result.get("joblib_expected")
        if path and os.path.exists(path):
            # backend_root contiene src/ → agrega al sys.path para pickle
            backend_root_local = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if backend_root_local not in sys.path:
                sys.path.insert(0, backend_root_local)
            result["sys_path_src"] = backend_root_local
            # Fix Python 3.11: las clases Cython de sklearn._loss._loss tienen
            # __module__ = '_loss' pero en Python 3.11 no se auto-registran en
            # sys.modules — registrar explícitamente antes de joblib.load().
            try:
                import sklearn._loss._loss as _sklearn_loss_ext
                if '_loss' not in sys.modules:
                    sys.modules['_loss'] = _sklearn_loss_ext
            except ImportError:
                pass
            model = joblib.load(path)
            result["load_success"] = True
            result["model_class"] = type(model).__name__
            from app.services.ml_inference import detect_feature_set, detect_meta_dim
            result["feature_set"] = detect_feature_set(model)
            result["meta_dim"] = detect_meta_dim(model.meta_learner)
        else:
            result["load_success"] = False
            result["load_skip"] = "archivo no encontrado"
    except Exception as e:
        result["load_success"] = False
        result["load_error"] = str(e)
        result["load_traceback"] = tb.format_exc()

    return result

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
