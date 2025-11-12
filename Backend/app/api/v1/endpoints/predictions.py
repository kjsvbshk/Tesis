"""
Predictions API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_espn_db, get_sys_db
from app.schemas.prediction import PredictionResponse, PredictionRequest
from app.services.prediction_service import PredictionService
from app.services.cache_service import cache_service
from app.services.snapshot_service import SnapshotService
from app.services.outbox_service import OutboxService
from app.services.audit_service import AuditService
from app.services.auth_service import get_current_user
from app.core.idempotency import check_idempotency_and_register
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=PredictionResponse)
async def get_prediction(
    prediction_request: PredictionRequest,
    idempotency_data: dict = Depends(check_idempotency_and_register),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_espn_db),
    sys_db: Session = Depends(get_sys_db)
):
    """
    Get prediction for a specific game
    Soporta idempotencia con X-Idempotency-Key header
    Usa caché con TTL para mejorar rendimiento
    """
    # Verificar si es duplicado
    if idempotency_data["is_duplicate"]:
        return idempotency_data["cached_response"]
    
    request_id = idempotency_data.get("request_id")
    request_service = idempotency_data["request_service"]
    
    # Marcar como procesando
    if request_id:
        await request_service.mark_request_processing(request_id)
    
    try:
        # Generar clave de caché
        cache_key = cache_service._generate_key(
            "prediction",
            game_id=prediction_request.game_id,
            user_id=current_user.id
        )
        
        # Obtener del caché o generar nueva predicción
        async def fetch_prediction():
            prediction_service = PredictionService(sys_db)
            return await prediction_service.get_game_prediction(
                game_id=prediction_request.game_id,
                user_id=current_user.id,
                request_id=request_id
            )
        
        # Usar caché con stale-while-revalidate
        prediction = await cache_service.get_or_set(
            key=cache_key,
            fetch_func=fetch_prediction,
            ttl_seconds=300,  # 5 minutos
            stale_ttl_seconds=600,  # 10 minutos para stale
            allow_stale=True
        )
        
        # Crear snapshot de odds (RF-07)
        snapshot_service = SnapshotService(sys_db)
        snapshot = await snapshot_service.create_snapshot_for_request(
            request_id=request_id,
            game_id=prediction_request.game_id
        )
        
        # Almacenar respuesta para idempotencia
        if idempotency_data.get("x_idempotency_key"):
            idempotency_service = idempotency_data["idempotency_service"]
            await idempotency_service.store_response(
                request_key=idempotency_data["x_idempotency_key"],
                response_data=prediction.dict() if hasattr(prediction, 'dict') else prediction
            )
        
        # Marcar como completado
        if request_id:
            await request_service.mark_request_completed(request_id)
        
        # Publicar evento en outbox (RF-08)
        outbox_service = OutboxService(sys_db)
        await outbox_service.publish_prediction_completed(
            request_id=request_id,
            prediction_data=prediction.dict() if hasattr(prediction, 'dict') else prediction,
            commit=True
        )
        
        # Registrar en auditoría (RF-09)
        audit_service = AuditService(sys_db)
        await audit_service.log_prediction_action(
            action="prediction.completed",
            actor_user_id=current_user.id,
            prediction_id=request_id,  # Usar request_id como prediction_id temporalmente
            metadata={
                "game_id": prediction_request.game_id,
                "request_key": idempotency_data.get("x_idempotency_key"),
                "model_version": prediction.model_version if hasattr(prediction, 'model_version') else None
            },
            commit=True
        )
        
        return prediction
    
    except Exception as e:
        # Marcar como fallido
        if request_id:
            await request_service.mark_request_failed(request_id, str(e))
        raise HTTPException(status_code=500, detail=f"Error generating prediction: {str(e)}")

@router.get("/game/{game_id}", response_model=PredictionResponse)
async def get_game_prediction(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_espn_db),
    sys_db: Session = Depends(get_sys_db)
):
    """
    Get prediction for a specific game by ID
    Usa caché con TTL para mejorar rendimiento
    """
    try:
        # Generar clave de caché
        cache_key = cache_service._generate_key(
            "prediction",
            game_id=game_id,
            user_id=current_user.id
        )
        
        # Obtener del caché o generar nueva predicción
        async def fetch_prediction():
            prediction_service = PredictionService(sys_db)
            return await prediction_service.get_game_prediction(
                game_id=game_id,
                user_id=current_user.id
            )
        
        # Usar caché con stale-while-revalidate
        prediction = await cache_service.get_or_set(
            key=cache_key,
            fetch_func=fetch_prediction,
            ttl_seconds=300,  # 5 minutos
            stale_ttl_seconds=600,  # 10 minutos para stale
            allow_stale=True
        )
        
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating prediction: {str(e)}")

@router.get("/upcoming", response_model=List[PredictionResponse])
async def get_upcoming_predictions(
    days: int = Query(7, description="Number of days ahead to predict"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_espn_db)
):
    """Get predictions for upcoming games"""
    try:
        prediction_service = PredictionService(db)
        predictions = await prediction_service.get_upcoming_predictions(
            days=days,
            user_id=current_user.id
        )
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(e)}")

@router.get("/model/status")
async def get_model_status():
    """Get ML model status and information"""
    try:
        prediction_service = PredictionService(None)  # No DB needed for model status
        status = await prediction_service.get_model_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting model status: {str(e)}")

@router.post("/retrain")
async def retrain_model(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_espn_db)
):
    """Retrain the ML model (admin only)"""
    try:
        # For now, allow any user to retrain (in production, add admin check)
        prediction_service = PredictionService(db)
        result = await prediction_service.retrain_model()
        return {
            "message": "Model retraining initiated",
            "status": "success",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retraining model: {str(e)}")
