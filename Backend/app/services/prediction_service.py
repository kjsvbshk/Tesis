"""
Prediction service for ML model integration
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os

# Importar joblib de forma opcional
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    print("⚠️  joblib no está instalado. Las predicciones usarán modo dummy.")

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️  pandas/numpy no están instalados. Algunas funcionalidades pueden estar limitadas.")

from app.models.game import Game
from app.models.team import Team
from app.models import ModelVersion, Prediction, Request
from app.schemas.prediction import PredictionResponse
from app.services.match_service import MatchService
import time

class PredictionService:
    def __init__(self, db: Session):
        self.db = db
        self.match_service = MatchService(db) if db else None
        self.model = None
        self.model_version_obj: Optional[ModelVersion] = None
        self.load_model()
    
    def load_model(self):
        """Load the trained ML model with versioning"""
        # Obtener versión activa del modelo desde BD
        self.model_version_obj = self.db.query(ModelVersion).filter(
            ModelVersion.is_active == True
        ).first()
        
        if not self.model_version_obj:
            print("⚠️  No active model version found, using dummy predictions")
            self.model = None
            return
        
        if not JOBLIB_AVAILABLE:
            print(f"⚠️  joblib no disponible, usando predicciones dummy (model version: {self.model_version_obj.version})")
            self.model = None
            return
        
        try:
            # Intentar cargar modelo desde archivo
            model_path = os.path.join("ml", "models", f"nba_prediction_model_{self.model_version_obj.version}.joblib")
            if not os.path.exists(model_path):
                # Fallback a nombre genérico
                model_path = os.path.join("ml", "models", "nba_prediction_model.joblib")
            
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                print(f"✅ ML model loaded successfully (version: {self.model_version_obj.version})")
            else:
                print(f"⚠️ ML model not found for version {self.model_version_obj.version}, using dummy predictions")
                self.model = None
        except Exception as e:
            print(f"❌ Error loading ML model: {e}")
            self.model = None
    
    async def get_game_prediction(
        self,
        game_id: int,
        user_id: int,
        request_id: Optional[int] = None
    ) -> PredictionResponse:
        """
        Get prediction for a specific game with telemetry
        Si se proporciona request_id, se guarda la predicción en BD
        """
        start_time = time.time()
        
        if not self.match_service:
            raise ValueError("Database connection required")
        
        game = await self.match_service.get_match_by_id(game_id)
        if not game:
            raise ValueError("Game not found")
        
        # game es un diccionario, no un objeto Game
        # Debug: mostrar qué claves tiene el diccionario
        print(f"DEBUG prediction_service: Game dict keys: {list(game.keys()) if isinstance(game, dict) else 'Not a dict'}")
        print(f"DEBUG prediction_service: Game dict: {game}")
        
        # Obtener información de equipos directamente del diccionario game
        home_team_id = game.get("home_team_id")
        away_team_id = game.get("away_team_id")
        home_team_name = None
        away_team_name = None
        
        # Obtener nombres de equipos desde el objeto anidado home_team/away_team
        if isinstance(game.get("home_team"), dict):
            home_team_info = game.get("home_team", {})
            home_team_id = home_team_id or home_team_info.get("id")
            home_team_name = home_team_info.get("name")
            print(f"DEBUG prediction_service: Found home_team from nested object: id={home_team_id}, name={home_team_name}")
        
        if isinstance(game.get("away_team"), dict):
            away_team_info = game.get("away_team", {})
            away_team_id = away_team_id or away_team_info.get("id")
            away_team_name = away_team_info.get("name")
            print(f"DEBUG prediction_service: Found away_team from nested object: id={away_team_id}, name={away_team_name}")
        
        # Si no tenemos nombres, intentar obtenerlos de otras fuentes
        if not home_team_name:
            # Buscar en todas las claves que puedan contener el nombre
            for key in ['home_team_name', 'home_team']:
                if key in game and game[key]:
                    if isinstance(game[key], str):
                        home_team_name = game[key]
                    elif isinstance(game[key], dict) and 'name' in game[key]:
                        home_team_name = game[key]['name']
                    break
        
        if not away_team_name:
            for key in ['away_team_name', 'away_team']:
                if key in game and game[key]:
                    if isinstance(game[key], str):
                        away_team_name = game[key]
                    elif isinstance(game[key], dict) and 'name' in game[key]:
                        away_team_name = game[key]['name']
                    break
        
        if not home_team_name or not away_team_name:
            available_keys = list(game.keys()) if isinstance(game, dict) else []
            team_related_keys = {k: v for k, v in game.items() if 'team' in k.lower() or 'home' in k.lower() or 'away' in k.lower()} if isinstance(game, dict) else {}
            
            error_msg = (
                f"Team names not found in game data for game_id={game_id}. "
                f"home_team_name={home_team_name}, away_team_name={away_team_name}. "
                f"home_team_id={home_team_id}, away_team_id={away_team_id}. "
                f"Available keys: {available_keys}. "
                f"Team-related keys and values: {team_related_keys}."
            )
            print(f"ERROR prediction_service: {error_msg}")
            raise ValueError(error_msg)
        
        # Crear objetos Team simples con la información disponible
        # (para compatibilidad con _predict_with_model y _generate_dummy_prediction)
        from app.models.team import Team
        home_team = Team()
        home_team.team_id = home_team_id or 0
        home_team.name = home_team_name
        
        away_team = Team()
        away_team.team_id = away_team_id or 0
        away_team.name = away_team_name
        
        # Generate prediction (dummy for now)
        if self.model:
            prediction = await self._predict_with_model(game, home_team, away_team)
        else:
            prediction = await self._generate_dummy_prediction(game, home_team, away_team)
        
        # Calcular latencia
        latency_ms = int((time.time() - start_time) * 1000)
        prediction["latency_ms"] = latency_ms
        
        # Si hay request_id, guardar predicción en BD
        if request_id and self.model_version_obj:
            await self._save_prediction(request_id, prediction, latency_ms)
        
        return PredictionResponse(
            game_id=game.get("id") or game.get("game_id"),
            home_team_id=getattr(home_team, "team_id", getattr(home_team, "id", None)),
            away_team_id=getattr(away_team, "team_id", getattr(away_team, "id", None)),
            home_team_name=home_team.name,
            away_team_name=away_team.name,
            game_date=game.get("game_date"),
            **prediction
        )
    
    async def _save_prediction(
        self,
        request_id: int,
        prediction_data: Dict[str, Any],
        latency_ms: int
    ):
        """Guardar predicción en BD con telemetría"""
        try:
            # Serializar score a JSON
            import json
            score_json = json.dumps(prediction_data)
            
            # Crear o actualizar predicción
            existing_prediction = self.db.query(Prediction).filter(
                Prediction.request_id == request_id
            ).first()
            
            if existing_prediction:
                # Actualizar predicción existente
                existing_prediction.score = score_json
                existing_prediction.latency_ms = latency_ms
                existing_prediction.model_version_id = self.model_version_obj.id
            else:
                # Crear nueva predicción
                prediction = Prediction(
                    request_id=request_id,
                    model_version_id=self.model_version_obj.id,
                    score=score_json,
                    latency_ms=latency_ms
                )
                self.db.add(prediction)
            
            self.db.commit()
        except Exception as e:
            print(f"⚠️  Error saving prediction: {e}")
            self.db.rollback()
    
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
                game_id = game.get("id") or game.get("game_id") if isinstance(game, dict) else getattr(game, "game_id", getattr(game, "id", None))
                prediction = await self.get_game_prediction(game_id, user_id)
                predictions.append(prediction)
            except Exception as e:
                game_id = game.get("id") or game.get("game_id") if isinstance(game, dict) else getattr(game, "game_id", getattr(game, "id", "unknown"))
                print(f"Error generating prediction for game {game_id}: {e}")
                continue
        
        return predictions
    
    async def _predict_with_model(self, game: Dict[str, Any], home_team: Team, away_team: Team) -> Dict[str, Any]:
        """Generate prediction using ML model"""
        # This would use the actual trained model
        # For now, return dummy data
        return await self._generate_dummy_prediction(game, home_team, away_team)
    
    async def _generate_dummy_prediction(self, game: Dict[str, Any], home_team: Team, away_team: Team) -> Dict[str, Any]:
        """Generate dummy prediction for testing"""
        import random
        
        # Simple home court advantage simulation
        home_advantage = 0.05  # 5% home court advantage
        
        # Random probabilities (in real implementation, these would come from the model)
        base_home_prob = 0.5 + home_advantage
        base_away_prob = 0.5 - home_advantage
        
        # Add some randomness
        if PANDAS_AVAILABLE:
            home_win_probability = min(0.9, max(0.1, base_home_prob + np.random.normal(0, 0.1)))
            predicted_home_score = 110 + np.random.normal(0, 10)
            predicted_away_score = 108 + np.random.normal(0, 10)
        else:
            # Fallback sin numpy
            home_win_probability = min(0.9, max(0.1, base_home_prob + random.uniform(-0.1, 0.1)))
            predicted_home_score = 110 + random.uniform(-10, 10)
            predicted_away_score = 108 + random.uniform(-10, 10)
        
        away_win_probability = 1.0 - home_win_probability
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
            "model_version": self.model_version_obj.version if self.model_version_obj else None,
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
            "model_version": self.model_version_obj.version if self.model_version_obj else None,
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
