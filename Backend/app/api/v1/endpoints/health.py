"""
Health and metrics endpoints for RF-14
SLOs expuestos (métricas/health) y endpoints de readiness/liveness
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_sys_db, sys_engine, espn_engine
from app.models import Request, AuditLog, Outbox, Prediction
from app.services.cache_service import cache_service

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    RF-14: Endpoint básico de salud
    """
    return {
        "status": "healthy",
        "service": "nba-bets-api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/liveness")
async def liveness_check():
    """
    Liveness probe endpoint
    RF-14: Verifica que la aplicación esté viva
    """
    try:
        # Verificar que la aplicación pueda responder
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not alive: {str(e)}")


@router.get("/readiness")
async def readiness_check(db: Session = Depends(get_sys_db)):
    """
    Readiness probe endpoint
    RF-14: Verifica que la aplicación esté lista para recibir tráfico
    """
    try:
        # Verificar conexión a BD app
        db.execute(text("SELECT 1"))
        
        # Verificar conexión a BD espn
        with espn_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_sys_db)):
    """
    Metrics endpoint
    RF-14: Expone métricas clave del sistema
    """
    try:
        # Métricas de requests
        total_requests = db.query(Request).count()
        completed_requests = db.query(Request).filter(Request.status == "completed").count()
        failed_requests = db.query(Request).filter(Request.status == "failed").count()
        processing_requests = db.query(Request).filter(Request.status == "processing").count()
        
        # Métricas de auditoría
        total_audit_logs = db.query(AuditLog).count()
        
        # Métricas de outbox
        total_outbox_events = db.query(Outbox).count()
        unpublished_events = db.query(Outbox).filter(Outbox.published_at.is_(None)).count()
        
        # Métricas de predicciones
        total_predictions = db.query(Prediction).count()
        
        # Métricas de caché
        cache_status = await cache_service.get_status()
        
        # Calcular tasas de éxito
        success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        failure_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "requests": {
                "total": total_requests,
                "completed": completed_requests,
                "failed": failed_requests,
                "processing": processing_requests,
                "success_rate": round(success_rate, 2),
                "failure_rate": round(failure_rate, 2)
            },
            "audit": {
                "total_logs": total_audit_logs
            },
            "outbox": {
                "total_events": total_outbox_events,
                "unpublished_events": unpublished_events,
                "published_events": total_outbox_events - unpublished_events
            },
            "predictions": {
                "total": total_predictions
            },
            "cache": cache_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")


@router.get("/metrics/requests")
async def get_request_metrics(
    date_from: datetime = None,
    date_to: datetime = None,
    db: Session = Depends(get_sys_db)
):
    """
    Métricas detalladas de requests
    RF-14: Métricas específicas de requests
    """
    try:
        query = db.query(Request)
        
        if date_from:
            query = query.filter(Request.created_at >= date_from)
        if date_to:
            query = query.filter(Request.created_at <= date_to)
        
        total = query.count()
        completed = query.filter(Request.status == "completed").count()
        failed = query.filter(Request.status == "failed").count()
        processing = query.filter(Request.status == "processing").count()
        
        # Calcular latencia promedio (si está disponible en predictions)
        predictions = db.query(Prediction).all()
        avg_latency = sum(p.latency_ms for p in predictions if p.latency_ms) / len(predictions) if predictions else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "period": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None
            },
            "requests": {
                "total": total,
                "completed": completed,
                "failed": failed,
                "processing": processing,
                "success_rate": round((completed / total * 100) if total > 0 else 0, 2),
                "failure_rate": round((failed / total * 100) if total > 0 else 0, 2)
            },
            "performance": {
                "avg_latency_ms": round(avg_latency, 2) if avg_latency > 0 else None,
                "total_predictions": len(predictions)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting request metrics: {str(e)}")

