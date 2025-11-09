"""
Predictions API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.prediction import PredictionResponse, PredictionRequest
from app.services.prediction_service import PredictionService
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=PredictionResponse)
async def get_prediction(
    prediction_request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get prediction for a specific game"""
    try:
        prediction_service = PredictionService(db)
        prediction = await prediction_service.get_game_prediction(
            game_id=prediction_request.game_id,
            user_id=current_user.id
        )
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating prediction: {str(e)}")

@router.get("/game/{game_id}", response_model=PredictionResponse)
async def get_game_prediction(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get prediction for a specific game by ID"""
    try:
        prediction_service = PredictionService(db)
        prediction = await prediction_service.get_game_prediction(
            game_id=game_id,
            user_id=current_user.id
        )
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating prediction: {str(e)}")

@router.get("/upcoming", response_model=List[PredictionResponse])
async def get_upcoming_predictions(
    days: int = Query(7, description="Number of days ahead to predict"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
