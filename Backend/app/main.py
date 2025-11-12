"""
NBA Bets Backend - FastAPI Application
Main application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import sys_engine, espn_engine, SysBase, EspnBase
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:4173",
    ],  # React/Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize database tables and start background workers"""
    try:
        # IMPORTANTE: Crear primero las tablas de espn porque app tiene referencias a espn
        # Crear tablas en Neon (esquema espn)
        EspnBase.metadata.create_all(bind=espn_engine)
        print("✅ Database tables created in Neon (schema: espn)")
        
        # Crear tablas en Neon (esquema app) - después de espn
        SysBase.metadata.create_all(bind=sys_engine)
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

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
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
