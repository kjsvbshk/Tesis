"""
Prediction Pydantic schemas
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class PredictionRequest(BaseModel):
    game_id: int

class PredictionResponse(BaseModel):
    game_id: int
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    game_date: datetime
    
    # Predictions
    home_win_probability: float
    away_win_probability: float
    predicted_home_score: float
    predicted_away_score: float
    predicted_total: float
    
    # Betting recommendations
    recommended_bet: Optional[str] = None  # "home", "away", "over", "under", "none"
    expected_value: Optional[float] = None
    confidence_score: float
    
    # Model information
    model_version: str
    prediction_timestamp: datetime
    
    # Additional features
    features_used: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
