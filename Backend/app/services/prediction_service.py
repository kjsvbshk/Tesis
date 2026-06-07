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
    print("⚠️  joblib no está instalado — instalar con: pip install joblib. Las predicciones no están disponibles.")

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
from app.services.feature_extractor import (
    FeatureExtractor,
    FeaturesNotAvailableError,
    FeatureExtractorError,
)
from app.services.ml_inference import (
    InferenceError,
    ModelNotLoadedError,
    detect_feature_set,
    predict_full_robust,
    extract_single_sample,
    validate_prediction,
)
from app.core.config import settings
import time
import logging

logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(self, db: Session):
        self.db = db
        self.match_service = MatchService(db) if db else None
        self.model = None
        self.model_version_obj: Optional[ModelVersion] = None
        self.load_model()
    
    def load_model(self):
        """Load the trained ML model with versioning.

        Sprint 1: logging detallado para diagnosticar fallos de carga.
        Imprime la versión activa, el path resuelto y, si joblib.load falla,
        muestra el tipo de la excepción además del mensaje, para distinguir
        entre file-not-found, unpickle error o ModuleNotFoundError (el caso
        típico cuando el .joblib se serializó con clases que ya no existen).
        """
        # Obtener versión activa del modelo desde BD
        self.model_version_obj = self.db.query(ModelVersion).filter(
            ModelVersion.is_active == True
        ).first()

        if not self.model_version_obj:
            print("[load_model] ⚠️  No active model version found in app.model_versions")
            self.model = None
            return

        if not JOBLIB_AVAILABLE:
            print(f"[load_model] ❌ joblib no disponible — instalar con: pip install joblib"
                  f" (model version: {self.model_version_obj.version})")
            self.model = None
            return

        try:
            # Resolver MODEL_DIR como ruta absoluta relativa a este archivo si es relativa
            model_dir = settings.MODEL_DIR
            if not os.path.isabs(model_dir):
                # Relativo al directorio raíz del Backend (dos niveles arriba de este archivo)
                backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                model_dir = os.path.normpath(os.path.join(backend_root, model_dir))

            version = self.model_version_obj.version
            model_path = os.path.join(model_dir, f"nba_prediction_model_{version}.joblib")
            fallback_path = os.path.join(model_dir, "nba_prediction_model.joblib")

            print(f"[load_model] versión activa: {version}")
            print(f"[load_model] MODEL_DIR resuelto: {model_dir}")
            print(f"[load_model] intentando: {model_path} (existe={os.path.exists(model_path)})")

            chosen_path = None
            if os.path.exists(model_path):
                chosen_path = model_path
            elif os.path.exists(fallback_path):
                chosen_path = fallback_path
                print(f"[load_model] usando fallback genérico: {fallback_path}")

            if chosen_path is None:
                print(f"[load_model] ❌ NO se encontró ningún .joblib en {model_dir}")
                print(f"[load_model]    archivos disponibles: "
                      f"{os.listdir(model_dir) if os.path.isdir(model_dir) else 'directorio NO existe'}")
                self.model = None
                return

            # Los .joblib se serializaron con clases registradas como
            # `src.models.ensemble.NBAEnsemble` (porque train.py corría desde
            # ML/ con `src` como package). Al deserializar desde Backend hay
            # que registrar ML/ en sys.path para que pickle encuentre `src.*`.
            import sys
            ml_root = os.path.normpath(os.path.join(model_dir, ".."))  # ML/
            if ml_root not in sys.path:
                sys.path.insert(0, ml_root)
                print(f"[load_model] sys.path += {ml_root} (para resolver `src.*` del pickle)")

            # Cargar el joblib — distinguir tipos de error para diagnóstico
            try:
                self.model = joblib.load(chosen_path)
            except ModuleNotFoundError as e:
                # Típico cuando el .joblib se serializó con imports que ya no existen
                # (p. ej. NBAEnsemble en versiones antiguas)
                print(f"[load_model] ❌ ModuleNotFoundError al cargar {chosen_path}: {e}")
                print(f"[load_model]    el .joblib referencia un módulo que ya no existe; "
                      f"hay que re-entrenar la versión {version}")
                self.model = None
                return
            except AttributeError as e:
                print(f"[load_model] ❌ AttributeError al cargar {chosen_path}: {e}")
                print(f"[load_model]    la clase del modelo cambió desde que se serializó este .joblib; "
                      f"re-entrenar la versión {version} con el código actual")
                self.model = None
                return

            print(f"[load_model] ✅ ML model loaded ({type(self.model).__name__}) "
                  f"version={version} path={chosen_path}")
            # Diagnóstico adicional para entender qué espera el modelo
            try:
                from app.services.ml_inference import detect_feature_set, detect_meta_dim
                fs = detect_feature_set(self.model)
                md = detect_meta_dim(self.model.meta_learner)
                print(f"[load_model]    feature_set inferido: {fs}, meta_dim: {md}")
            except Exception as diag_e:
                print(f"[load_model]    (no se pudo inferir feature_set/meta_dim: {diag_e})")

        except Exception as e:
            print(f"[load_model] ❌ Error inesperado: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
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
        from app.models.team import Team
        home_team = Team()
        home_team.team_id = home_team_id or 0
        home_team.name = home_team_name
        
        away_team = Team()
        away_team.team_id = away_team_id or 0
        away_team.name = away_team_name
        
        # El sistema SOLO devuelve predicciones reales del modelo ML.
        # Si el modelo no está cargado, se lanza 503 — nunca se devuelven
        # valores artificiales que el usuario podría confundir con resultados reales.
        if not self.model:
            raise ModelNotLoadedError(
                "El modelo ML no está disponible en este momento. "
                "Verifique que el archivo .joblib esté configurado y que "
                "app.model_versions tenga una versión activa."
            )
        try:
            prediction = await self._predict_with_model(game, home_team, away_team)
        except FeaturesNotAvailableError:
            # Partido sin features pre-calculadas → el endpoint REST devuelve 422
            raise

        # Calcular latencia HTTP total (incluye lookup de game, features, inferencia)
        latency_ms = int((time.time() - start_time) * 1000)
        prediction["latency_ms"] = latency_ms

        # Si hay request_id, guardar predicción en BD
        if request_id and self.model_version_obj:
            await self._save_prediction(request_id, prediction, latency_ms)

        # Filtrar a campos conocidos del schema para evitar ValidationError
        # cuando _predict_with_model devuelve claves auxiliares ya envueltas.
        allowed_keys = set(PredictionResponse.model_fields.keys())
        clean_prediction = {k: v for k, v in prediction.items() if k in allowed_keys}

        return PredictionResponse(
            game_id=game.get("id") or game.get("game_id"),
            home_team_id=getattr(home_team, "team_id", getattr(home_team, "id", None)),
            away_team_id=getattr(away_team, "team_id", getattr(away_team, "id", None)),
            home_team_name=home_team.name,
            away_team_name=away_team.name,
            game_date=game.get("game_date"),
            **clean_prediction
        )
    
    async def _save_prediction(
        self,
        request_id: int,
        prediction_data: Dict[str, Any],
        latency_ms: int
    ):
        """Guardar predicción en BD con telemetría"""
        try:
            # Serializar score a JSON - convertir datetime a string
            import json
            from datetime import datetime, date
            
            # Función helper para convertir datetime/date a string
            def json_serial(obj):
                """JSON serializer para objetos datetime/date"""
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            # Convertir prediction_data a dict serializable
            serializable_data = {}
            for key, value in prediction_data.items():
                if isinstance(value, (datetime, date)):
                    serializable_data[key] = value.isoformat()
                elif isinstance(value, dict):
                    # Recursivamente convertir dicts anidados
                    serializable_data[key] = json.loads(json.dumps(value, default=json_serial))
                else:
                    serializable_data[key] = value
            
            score_json = json.dumps(serializable_data, default=json_serial)
            
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
        """
        Devuelve predicciones para partidos futuros de los próximos `days` días.

        Consulta espn.games directamente filtrando por fecha y score=0 (no jugados).
        Para cada partido usa LiveFeatureExtractor para calcular las features en vivo
        y producir una predicción real con el modelo cargado.
        """
        from sqlalchemy import text as sql_text
        from datetime import datetime, timedelta, date

        today = datetime.now().date()
        future_date = today + timedelta(days=days)

        # Obtener partidos futuros desde espn.games
        query = sql_text("""
            SELECT game_id, fecha, home_team, away_team, home_score, away_score, status
            FROM espn.games
            WHERE fecha >= :today
              AND fecha <= :future
              AND (home_score = 0 OR home_score IS NULL)
              AND (away_score = 0 OR away_score IS NULL)
              AND home_team != 'TBD' AND away_team != 'TBD'
              AND home_team IS NOT NULL AND away_team IS NOT NULL
            ORDER BY fecha ASC
        """)
        rows = self.db.execute(query, {
            "today": str(today),
            "future": str(future_date),
        }).mappings().fetchall()

        if not rows:
            return []

        from app.services.live_feature_extractor import LiveFeatureExtractor, LiveFeaturesError
        from app.services.ml_inference import detect_feature_set, predict_full_robust, extract_single_sample, validate_prediction, ModelNotLoadedError
        from app.schemas.prediction import PredictionResponse

        if self.model is None:
            raise ModelNotLoadedError("No hay modelo cargado.")

        try:
            feature_set = detect_feature_set(self.model)
        except Exception:
            feature_set = "v2"

        live_extractor = LiveFeatureExtractor(self.db)
        predictions = []

        for row in rows:
            game_id   = int(row["game_id"])
            home_name = row["home_team"]
            away_name = row["away_team"]
            game_date = row["fecha"]
            if isinstance(game_date, str):
                game_date = datetime.strptime(game_date[:10], "%Y-%m-%d").date()

            try:
                import time
                t0 = time.time()
                X = live_extractor.build_feature_vector(
                    home_team=home_name,
                    away_team=away_name,
                    game_date=game_date,
                    feature_set=feature_set,
                    game_id=game_id,
                )
                features_summary = live_extractor.get_features_summary(
                    home_team=home_name,
                    away_team=away_name,
                    game_date=game_date,
                    feature_set=feature_set,
                    game_id=game_id,
                )
                full_output = predict_full_robust(self.model, X)
                inference_ms = int((time.time() - t0) * 1000)

                scalar = extract_single_sample(full_output, idx=0)
                validate_prediction(scalar)

                home_proba = scalar["home_win_probability"]
                away_proba = scalar["away_win_probability"]

                if home_proba > 0.6:
                    recommended_bet, ev = "home", round(home_proba * 1.8 - 1.0, 3)
                elif away_proba > 0.6:
                    recommended_bet, ev = "away", round(away_proba * 1.8 - 1.0, 3)
                else:
                    recommended_bet, ev = "none", 0.0

                pred = PredictionResponse(
                    game_id=game_id,
                    home_team_id=None,
                    away_team_id=None,
                    home_team_name=home_name,
                    away_team_name=away_name,
                    home_win_probability=round(home_proba, 4),
                    away_win_probability=round(away_proba, 4),
                    predicted_home_score=round(scalar.get("predicted_home_score") or 0.0, 1),
                    predicted_away_score=round(scalar.get("predicted_away_score") or 0.0, 1),
                    predicted_total=round(scalar.get("predicted_total") or 0.0, 1),
                    predicted_margin=round(scalar.get("predicted_margin") or 0.0, 2),
                    recommended_bet=recommended_bet,
                    expected_value=ev,
                    confidence_score=round(max(home_proba, away_proba), 3),
                    model_version=self.model_version_obj.version if self.model_version_obj else "unknown",
                    prediction_timestamp=datetime.utcnow(),
                    game_date=game_date,
                    features_used=features_summary,
                    inference_latency_ms=inference_ms,
                )
                predictions.append(pred)

            except (LiveFeaturesError, Exception) as e:
                logger.warning(f"Upcoming prediction falló para game {game_id} "
                               f"({away_name} @ {home_name}): {e}")
                continue

        return predictions
    
    async def _predict_with_model(self, game: Dict[str, Any], home_team: Team, away_team: Team) -> Dict[str, Any]:
        """Generate prediction using the loaded ML model (Sprint 1).

        Flujo:
          1. Inferir el feature_set que espera el modelo (v1 = 21, v2 = 33).
          2. Consultar features pre-calculadas desde ml.ml_ready_games.
          3. Invocar predict_full_robust sobre los componentes del ensemble.
          4. Validar rangos sanos (probabilidades en [0,1], scores realistas).
          5. Construir el dict de respuesta para mapear a PredictionResponse.

        Raises:
            ModelNotLoadedError    si el modelo no se pudo cargar.
            FeaturesNotAvailableError si el partido no existe en ml.ml_ready_games.
            InferenceError         si el modelo produce salida inválida.
        """
        if self.model is None:
            raise ModelNotLoadedError(
                "El servicio recibió una solicitud de predicción pero no hay "
                "modelo cargado. Verificar sys.model_versions y MODEL_DIR."
            )

        game_id = game.get("id") or game.get("game_id")
        if game_id is None:
            raise InferenceError("Game sin identificador (id/game_id)")

        # 1. Detectar feature set esperado por el modelo cargado
        try:
            feature_set = detect_feature_set(self.model)
        except InferenceError as e:
            logger.error(f"No se pudo inferir feature_set para game {game_id}: {e}")
            raise

        # 2. Extraer features desde ml.ml_ready_games (partidos históricos) o
        #    LiveFeatureExtractor (partidos futuros sin fila pre-calculada).
        extractor = FeatureExtractor(self.db)
        try:
            X = extractor.build_feature_vector(game_id, feature_set=feature_set)
            features_summary = extractor.get_features_summary(game_id, feature_set=feature_set)
        except FeaturesNotAvailableError:
            # Partido futuro: intentar con LiveFeatureExtractor
            logger.info(
                f"game {game_id} no está en ml_ready_games — "
                "intentando LiveFeatureExtractor para partido futuro"
            )
            home_name = home_team.name if home_team else game.get("home_team")
            away_name = away_team.name if away_team else game.get("away_team")
            raw_date  = game.get("game_date") or game.get("fecha") or game.get("date")
            if isinstance(raw_date, str):
                from datetime import datetime
                try:
                    game_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
                except ValueError:
                    game_date = datetime.now().date()
            elif raw_date is None:
                from datetime import datetime
                game_date = datetime.now().date()
            else:
                game_date = raw_date

            if not home_name or not away_name:
                raise FeaturesNotAvailableError(
                    f"Partido {game_id} no tiene features pre-calculadas ni "
                    "nombres de equipo válidos para calcularlas en vivo."
                )

            from app.services.live_feature_extractor import LiveFeatureExtractor, LiveFeaturesError
            live_extractor = LiveFeatureExtractor(self.db)
            try:
                X = live_extractor.build_feature_vector(
                    home_team=home_name,
                    away_team=away_name,
                    game_date=game_date,
                    feature_set=feature_set,
                    game_id=game_id,
                )
                features_summary = live_extractor.get_features_summary(
                    home_team=home_name,
                    away_team=away_name,
                    game_date=game_date,
                    feature_set=feature_set,
                    game_id=game_id,
                )
                logger.info(
                    f"game {game_id}: features en vivo calculadas "
                    f"(missing={features_summary.get('missing_count', '?')})"
                )
            except LiveFeaturesError as lfe:
                raise FeaturesNotAvailableError(str(lfe))
        except FeatureExtractorError as e:
            logger.error(f"Error extrayendo features para game {game_id}: {e}")
            raise InferenceError(f"Feature extraction falló: {e}")

        # 3. Invocar el modelo (con timing aislado de la inferencia)
        inference_start = time.time()
        try:
            full_output = predict_full_robust(self.model, X)
        except Exception as e:
            logger.error(f"Modelo falló al predecir game {game_id}: {e}")
            raise InferenceError(f"predict_full_robust falló: {e}")
        inference_ms = int((time.time() - inference_start) * 1000)

        # 4. Reducir a escalares y validar
        scalar = extract_single_sample(full_output, idx=0)
        validate_prediction(scalar)

        # 5. Construir payload con derivados (recomendación de apuesta, EV, confianza)
        home_proba = scalar["home_win_probability"]
        away_proba = scalar["away_win_probability"]
        # Umbral de confianza: >60% probabilidad de victoria → recomendar ese equipo.
        if home_proba > 0.6:
            recommended_bet = "home"
            expected_value = round(home_proba * 1.8 - 1.0, 3)
        elif away_proba > 0.6:
            recommended_bet = "away"
            expected_value = round(away_proba * 1.8 - 1.0, 3)
        else:
            recommended_bet = "none"
            expected_value = 0.0
        confidence_score = round(max(home_proba, away_proba), 3)

        # 6. Armar respuesta
        response: Dict[str, Any] = {
            "home_win_probability": round(home_proba, 4),
            "away_win_probability": round(away_proba, 4),
            "predicted_home_score": round(scalar.get("predicted_home_score") or 0.0, 1),
            "predicted_away_score": round(scalar.get("predicted_away_score") or 0.0, 1),
            "predicted_total": round(
                (scalar.get("predicted_total")
                 or ((scalar.get("predicted_home_score") or 0.0)
                     + (scalar.get("predicted_away_score") or 0.0))),
                1,
            ),
            "predicted_margin": (
                round(scalar["predicted_margin"], 2)
                if scalar.get("predicted_margin") is not None else None
            ),
            "recommended_bet": recommended_bet,
            "expected_value": expected_value,
            "confidence_score": confidence_score,
            "model_version": (
                self.model_version_obj.version if self.model_version_obj else "unknown"
            ),
            "prediction_timestamp": datetime.utcnow(),
            "features_used": features_summary,
            # Telemetría — útil para el dashboard de inferencia
            "inference_latency_ms": inference_ms,
        }

        # Team-props (v2.2.0+) si el modelo los expone
        if "team_props" in scalar:
            tp = scalar["team_props"]
            response["team_props"] = {
                "home": tp.get("home", {}),
                "away": tp.get("away", {}),
                "labels": tp.get("labels", {}),
            }

        # Señales auxiliares del Poisson (v2.1.x+) — útiles para auditoría
        for key in (
            "poisson_probability", "poisson_lambda1", "poisson_lambda2",
            "poisson_lambda3", "poisson_home_score", "poisson_away_score",
            "rf_probability",
        ):
            if scalar.get(key) is not None:
                response.setdefault("model_signals", {})[key] = round(scalar[key], 4)

        logger.info(
            f"Predicción game={game_id} model={response['model_version']} "
            f"P(home)={home_proba:.3f} inference_ms={inference_ms}"
        )
        return response
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Get ML model status and information"""
        metrics = None
        trained_at = None
        if self.model_version_obj and self.model_version_obj.model_metadata:
            raw = self.model_version_obj.model_metadata
            meta = raw if isinstance(raw, dict) else {}
            
            # Las métricas pueden estar en la raíz o dentro de una clave "metrics"
            metrics_source = meta.get("metrics", meta) if isinstance(meta.get("metrics"), dict) else meta
            
            metrics = {k: metrics_source[k] for k in ("log_loss", "brier_score", "roc_auc", "ece", "accuracy",
                                              "mae_margin", "mae_total") if k in metrics_source}
            
            trained_at = meta.get("trained_at") or (
                self.model_version_obj.created_at.isoformat()
                if self.model_version_obj.created_at else None
            )

        return {
            "model_loaded": self.model is not None,
            "model_version": self.model_version_obj.version if self.model_version_obj else None,
            "model_type": type(self.model).__name__ if self.model else "not_loaded",
            "trained_at": trained_at,
            "metrics": metrics,
            "status": "ready" if self.model else "unavailable",
            "using_real_predictions": self.model is not None,
        }
    
    async def retrain_model(self) -> Dict[str, Any]:
        """Retrain the ML model"""
        # This would implement the actual retraining logic
        return {
            "status": "retraining_initiated",
            "message": "Model retraining started. This may take several minutes.",
            "estimated_completion": "10-15 minutes"
        }
