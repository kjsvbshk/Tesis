"""
Prediction Pydantic schemas
"""

from pydantic import BaseModel, field_serializer
from typing import Optional, Dict, Any
from datetime import datetime, date

class PredictionRequest(BaseModel):
    game_id: int

class PredictionResponse(BaseModel):
    game_id: int
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    game_date: Optional[datetime] = None
    
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
    
    @field_serializer('game_date')
    def serialize_game_date(self, value: Optional[datetime]) -> Optional[str]:
        """Serializar game_date a ISO format string"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value)
    
    @field_serializer('prediction_timestamp')
    def serialize_prediction_timestamp(self, value: datetime) -> str:
        """Serializar prediction_timestamp a ISO format string"""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None
        }
    
    def model_dump(self, **kwargs):
        """Override model_dump to ensure datetime serialization"""
        # Usar mode='json' para serializar correctamente los datetime
        mode = kwargs.pop('mode', 'python')
        if mode == 'json' or 'json' in str(kwargs.get('mode', '')):
            kwargs['mode'] = 'json'
        data = super().model_dump(**kwargs)
        # Convertir datetime a ISO format strings si aún no están convertidos
        if 'game_date' in data and data['game_date']:
            if isinstance(data['game_date'], (datetime, date)):
                data['game_date'] = data['game_date'].isoformat()
        if 'prediction_timestamp' in data and data['prediction_timestamp']:
            if isinstance(data['prediction_timestamp'], datetime):
                data['prediction_timestamp'] = data['prediction_timestamp'].isoformat()
        return data
    
    def dict(self, **kwargs):
        """Override dict for backward compatibility"""
        # Por defecto, usar mode='json' para serializar datetime correctamente
        if 'mode' not in kwargs:
            kwargs['mode'] = 'json'
        return self.model_dump(**kwargs)
