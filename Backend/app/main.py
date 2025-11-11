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
from app.models import user, bet, transaction  # Modelos app
from app.models import team, game, team_stats  # Modelos espn

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
    """Initialize database tables"""
    try:
        # IMPORTANTE: Crear primero las tablas de espn porque app tiene referencias a espn
        # Crear tablas en BD data (esquema espn)
        EspnBase.metadata.create_all(bind=espn_engine)
        print("✅ Database tables created in data.espn")
        
        # Crear tablas en BD data (esquema app) - después de espn
        SysBase.metadata.create_all(bind=sys_engine)
        print("✅ Database tables created in data.app")
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nba-bets-api"}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
