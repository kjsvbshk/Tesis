"""
Prediction service for ML model integration
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import joblib
import os
import pandas as pd
import numpy as np

from app.models.game import Game
from app.models.team import Team
from app.schemas.prediction import PredictionResponse
from app.services.match_service import MatchService

class PredictionService:
    def __init__(self, db: Session):
        self.db = db
        self.match_service = MatchService(db) if db else None
        self.model = None
        self.model_version = "1.0.0"
        self.load_model()
    
    def load_model(self):
        """Load the trained ML model"""
        try:
            model_path = os.path.join("ml", "models", "nba_prediction_model.joblib")
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                print("✅ ML model loaded successfully")
            else:
                print("⚠️ ML model not found, using dummy predictions")
                self.model = None
        except Exception as e:
            print(f"❌ Error loading ML model: {e}")
            self.model = None
    
    async def get_game_prediction(self, game_id: int, user_id: int) -> PredictionResponse:
        """Get prediction for a specific game"""
        if not self.match_service:
            raise ValueError("Database connection required")
        
        game = await self.match_service.get_match_by_id(game_id)
        if not game:
            raise ValueError("Game not found")
        
        home_team = await self.match_service.get_team_by_id(game.home_team_id)
        away_team = await self.match_service.get_team_by_id(game.away_team_id)
        
        if not home_team or not away_team:
            raise ValueError("Team information not found")
        
        # Generate prediction (dummy for now)
        if self.model:
            prediction = await self._predict_with_model(game, home_team, away_team)
        else:
            prediction = await self._generate_dummy_prediction(game, home_team, away_team)
        
        return PredictionResponse(
            game_id=game.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_team_name=home_team.name,
            away_team_name=away_team.name,
            game_date=game.game_date,
            **prediction
        )
    
    async def get_upcoming_predictions(self, days: int, user_id: int) -> List[PredictionResponse]:
        """Get predictions for upcoming games"""
        if not self.match_service:
            raise ValueError("Database connection required")
        
        today = datetime.now().date()
        future_date = today + timedelta(days=days)
        
        games = await self.match_service.get_matches(
            date_from=today,
            date_to=future_date,
            status="scheduled"
        )
        
        predictions = []
        for game in games:
            try:
                prediction = await self.get_game_prediction(game.id, user_id)
                predictions.append(prediction)
            except Exception as e:
                print(f"Error generating prediction for game {game.id}: {e}")
                continue
        
        return predictions
    
    async def _predict_with_model(self, game: Game, home_team: Team, away_team: Team) -> Dict[str, Any]:
        """Generate prediction using ML model"""
        # This would use the actual trained model
        # For now, return dummy data
        return await self._generate_dummy_prediction(game, home_team, away_team)
    
    async def _generate_dummy_prediction(self, game: Game, home_team: Team, away_team: Team) -> Dict[str, Any]:
        """Generate dummy prediction for testing"""
        # Simple home court advantage simulation
        home_advantage = 0.05  # 5% home court advantage
        
        # Random probabilities (in real implementation, these would come from the model)
        base_home_prob = 0.5 + home_advantage
        base_away_prob = 0.5 - home_advantage
        
        # Add some randomness
        home_win_probability = min(0.9, max(0.1, base_home_prob + np.random.normal(0, 0.1)))
        away_win_probability = 1.0 - home_win_probability
        
        # Predicted scores
        predicted_home_score = 110 + np.random.normal(0, 10)
        predicted_away_score = 108 + np.random.normal(0, 10)
        predicted_total = predicted_home_score + predicted_away_score
        
        # Betting recommendation
        if home_win_probability > 0.6:
            recommended_bet = "home"
            expected_value = (home_win_probability * 1.8) - 1.0  # Assuming 1.8 odds
        elif away_win_probability > 0.6:
            recommended_bet = "away"
            expected_value = (away_win_probability * 1.8) - 1.0
        else:
            recommended_bet = "none"
            expected_value = 0.0
        
        confidence_score = max(home_win_probability, away_win_probability)
        
        return {
            "home_win_probability": round(home_win_probability, 3),
            "away_win_probability": round(away_win_probability, 3),
            "predicted_home_score": round(predicted_home_score, 1),
            "predicted_away_score": round(predicted_away_score, 1),
            "predicted_total": round(predicted_total, 1),
            "recommended_bet": recommended_bet,
            "expected_value": round(expected_value, 3),
            "confidence_score": round(confidence_score, 3),
            "model_version": self.model_version,
            "prediction_timestamp": datetime.utcnow(),
            "features_used": {
                "home_team": home_team.name,
                "away_team": away_team.name,
                "home_court_advantage": home_advantage
            }
        }
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Get ML model status and information"""
        return {
            "model_loaded": self.model is not None,
            "model_version": self.model_version,
            "model_type": "RandomForest + XGBoost Ensemble" if self.model else "Dummy Predictor",
            "last_trained": "2024-01-01",  # Would be actual timestamp
            "accuracy": 0.65 if self.model else 0.0,  # Would be actual accuracy
            "status": "ready" if self.model else "dummy_mode"
        }
    
    async def retrain_model(self) -> Dict[str, Any]:
        """Retrain the ML model"""
        # This would implement the actual retraining logic
        return {
            "status": "retraining_initiated",
            "message": "Model retraining started. This may take several minutes.",
            "estimated_completion": "10-15 minutes"
        }
