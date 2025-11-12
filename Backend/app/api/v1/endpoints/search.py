"""
Search endpoints for RF-12
Búsqueda por request_id, request_key, event_id y rango de fechas
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_sys_db
from app.models import Request, IdempotencyKey, AuditLog, Outbox
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/requests")
async def search_requests(
    request_id: Optional[int] = Query(None, description="Buscar por request ID"),
    request_key: Optional[str] = Query(None, description="Buscar por request key"),
    event_id: Optional[int] = Query(None, description="Buscar por event ID (game_id)"),
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    user_id: Optional[int] = Query(None, description="Filtrar por usuario"),
    limit: int = Query(50, description="Número de resultados"),
    offset: int = Query(0, description="Offset para paginación"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Buscar requests por múltiples criterios
    RF-12: Búsqueda por request_id, request_key, event_id y rango de fechas
    """
    try:
        query = db.query(Request)
        
        if request_id:
            query = query.filter(Request.id == request_id)
        
        if request_key:
            query = query.filter(Request.request_key == request_key)
        
        if event_id:
            query = query.filter(Request.event_id == event_id)
        
        if date_from:
            query = query.filter(Request.created_at >= datetime.combine(date_from, datetime.min.time()))
        
        if date_to:
            query = query.filter(Request.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        if status:
            query = query.filter(Request.status == status)
        
        if user_id:
            query = query.filter(Request.user_id == user_id)
        
        total = query.count()
        results = query.order_by(Request.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": [
                {
                    "id": r.id,
                    "request_key": r.request_key,
                    "event_id": r.event_id,
                    "user_id": r.user_id,
                    "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching requests: {str(e)}")


@router.get("/idempotency-keys")
async def search_idempotency_keys(
    request_key: Optional[str] = Query(None, description="Buscar por request key"),
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
    limit: int = Query(50, description="Número de resultados"),
    offset: int = Query(0, description="Offset para paginación"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Buscar idempotency keys
    RF-12: Búsqueda por request_key y rango de fechas
    """
    try:
        query = db.query(IdempotencyKey)
        
        if request_key:
            query = query.filter(IdempotencyKey.request_key == request_key)
        
        if date_from:
            query = query.filter(IdempotencyKey.created_at >= datetime.combine(date_from, datetime.min.time()))
        
        if date_to:
            query = query.filter(IdempotencyKey.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        total = query.count()
        results = query.order_by(IdempotencyKey.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": [
                {
                    "id": k.id,
                    "request_key": k.request_key,
                    "request_id": k.request_id,
                    "created_at": k.created_at.isoformat() if k.created_at else None,
                    "expires_at": k.expires_at.isoformat() if k.expires_at else None
                }
                for k in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching idempotency keys: {str(e)}")


@router.get("/audit-logs")
async def search_audit_logs(
    actor_user_id: Optional[int] = Query(None, description="Filtrar por usuario actor"),
    action: Optional[str] = Query(None, description="Filtrar por acción"),
    resource_type: Optional[str] = Query(None, description="Filtrar por tipo de recurso"),
    resource_id: Optional[int] = Query(None, description="Filtrar por ID de recurso"),
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
    limit: int = Query(50, description="Número de resultados"),
    offset: int = Query(0, description="Offset para paginación"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Buscar logs de auditoría
    RF-12: Búsqueda por múltiples criterios y rango de fechas
    """
    try:
        from app.services.audit_service import AuditService
        
        audit_service = AuditService(db)
        
        date_from_dt = datetime.combine(date_from, datetime.min.time()) if date_from else None
        date_to_dt = datetime.combine(date_to, datetime.max.time()) if date_to else None
        
        results = await audit_service.get_audit_logs(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            date_from=date_from_dt,
            date_to=date_to_dt,
            limit=limit,
            offset=offset
        )
        
        return {
            "total": len(results),
            "limit": limit,
            "offset": offset,
            "results": [
                {
                    "id": log.id,
                    "actor_user_id": log.actor_user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "before": log.before,
                    "after": log.after,
                    "metadata": log.audit_metadata
                }
                for log in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching audit logs: {str(e)}")


@router.get("/events")
async def search_events(
    event_id: Optional[int] = Query(None, description="Buscar por event ID (game_id)"),
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
    limit: int = Query(50, description="Número de resultados"),
    offset: int = Query(0, description="Offset para paginación"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Buscar eventos relacionados con requests
    RF-12: Búsqueda por event_id y rango de fechas
    """
    try:
        query = db.query(Request).filter(Request.event_id.isnot(None))
        
        if event_id:
            query = query.filter(Request.event_id == event_id)
        
        if date_from:
            query = query.filter(Request.created_at >= datetime.combine(date_from, datetime.min.time()))
        
        if date_to:
            query = query.filter(Request.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        total = query.count()
        results = query.order_by(Request.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": [
                {
                    "event_id": r.event_id,
                    "request_id": r.id,
                    "request_key": r.request_key,
                    "user_id": r.user_id,
                    "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching events: {str(e)}")

