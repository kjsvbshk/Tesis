"""
Feature extractor para inferencia en tiempo de ejecución.

Lee la fila correspondiente al `game_id` desde `ml.ml_ready_games` (Neon) y
ordena las columnas exactamente igual que en el pipeline de entrenamiento
(`ML/src/training/train.py`), de modo que el vector de features `X` que se
pasa al modelo .joblib coincide en orden y dimensión con el que vio durante
fit.

Está pensado para Sprint 1: si la fila no existe en `ml.ml_ready_games`
(p. ej. partido futuro aún no procesado por el ETL), se levanta
`FeaturesNotAvailableError` y el endpoint REST debe devolver 422.

La extensión para construir features en runtime para partidos futuros queda
fuera del alcance de este sprint.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


# ---------------------------------------------------------------------------
# Feature sets — orden idéntico al de ML/src/training/train.py
# ---------------------------------------------------------------------------
# Si cambian las features en train.py, hay que actualizar también esta lista.
# Tests de integración detectarían el mismatch porque el predict del modelo
# fallaría con "X has N features but expecting M features".

V1_DIFF_FEATURES: List[str] = [
    "ppg_diff",
    "net_rating_diff_rolling",
    "rest_days_diff",
    "injuries_diff",
    "pace_diff",
    "off_rating_diff",
    "def_rating_diff",
    "reb_rolling_diff",
    "ast_rolling_diff",
    "tov_rolling_diff",
    "win_rate_diff",
]

V1_INDIVIDUAL_FEATURES: List[str] = [
    "home_ppg_last5",
    "away_ppg_last5",
    "home_rest_days",
    "away_rest_days",
    "home_b2b",
    "away_b2b",
    "home_injuries_count",
    "away_injuries_count",
    "home_win_rate_last10",
    "away_win_rate_last10",
]

V2_EXTRA_DIFF_FEATURES: List[str] = [
    "efg_pct_diff",
    "tov_rate_diff",
    "oreb_pct_diff",
    "dreb_pct_diff",
    "elo_diff",
    "streak_diff",
    "home_away_split_diff",
]

V2_EXTRA_INDIVIDUAL_FEATURES: List[str] = [
    "home_elo",
    "away_elo",
    "home_streak",
    "away_streak",
    "h2h_home_advantage",
]

# Features de odds de mercado (baja cobertura ~1.4%; pre-imputadas con mediana).
# Solo presentes cuando el modelo fue entrenado con --use-odds.
ODDS_FEATURES: List[str] = [
    "implied_prob_home",
    "implied_prob_away",
]

# Orden exacto que produce train.py: DIFF_FEATURES + INDIVIDUAL_FEATURES [+ ODDS_FEATURES]
V1_FEATURES: List[str] = V1_DIFF_FEATURES + V1_INDIVIDUAL_FEATURES                    # 21

V2_FEATURES: List[str] = (
    V1_DIFF_FEATURES
    + V2_EXTRA_DIFF_FEATURES
    + V1_INDIVIDUAL_FEATURES
    + V2_EXTRA_INDIVIDUAL_FEATURES
)  # 33

V2_ODDS_FEATURES: List[str] = V2_FEATURES + ODDS_FEATURES  # 35

assert len(V1_FEATURES)    == 21, f"V1 debe tener 21 features, tiene {len(V1_FEATURES)}"
assert len(V2_FEATURES)    == 33, f"V2 debe tener 33 features, tiene {len(V2_FEATURES)}"
assert len(V2_ODDS_FEATURES) == 35, f"V2+odds debe tener 35 features, tiene {len(V2_ODDS_FEATURES)}"

FEATURE_SETS: Dict[str, List[str]] = {
    "v1":      V1_FEATURES,
    "v2":      V2_FEATURES,
    "v2_odds": V2_ODDS_FEATURES,   # modelo entrenado con --use-odds
}


# ---------------------------------------------------------------------------
# Excepciones específicas del extractor
# ---------------------------------------------------------------------------

class FeatureExtractorError(Exception):
    """Error base del feature extractor."""


class FeaturesNotAvailableError(FeatureExtractorError):
    """No existe la fila en ml.ml_ready_games para el game_id solicitado.

    Causas típicas: el partido es muy reciente y el ETL `build_features.py`
    aún no lo ha procesado, o el game_id no corresponde a un partido NBA
    válido.
    """


class UnknownFeatureSetError(FeatureExtractorError):
    """El feature_set solicitado no es 'v1' ni 'v2'."""


# ---------------------------------------------------------------------------
# FeatureExtractor
# ---------------------------------------------------------------------------

class FeatureExtractor:
    """Extrae features pre-calculadas de `ml.ml_ready_games` para inferencia.

    Args:
        db: Session SQLAlchemy. Cualquier session sirve siempre que pueda
            ejecutar SQL con esquema explícito (`ml.ml_ready_games`).
    """

    def __init__(self, db: Session):
        self.db = db
        self.ml_schema = getattr(settings, "ML_SCHEMA", "ml")
        # Cache por instancia: evita ejecutar la misma SELECT dos veces dentro
        # de un mismo request (una para build_feature_vector y otra para
        # get_features_summary). El cache es local al request porque cada
        # request crea su propia instancia de PredictionService → FeatureExtractor.
        self._cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Lectura desde BD
    # ------------------------------------------------------------------

    def get_features_for_game(self, game_id: int) -> Dict[str, Any]:
        """Devuelve el dict de features pre-calculadas para el game_id dado.

        Raises:
            FeaturesNotAvailableError si no hay fila en ml.ml_ready_games.
        """
        gid = int(game_id)
        if gid in self._cache:
            return self._cache[gid]

        query = text(
            f"SELECT * FROM {self.ml_schema}.ml_ready_games "
            "WHERE game_id = :gid LIMIT 1"
        )
        result = self.db.execute(query, {"gid": gid}).mappings().first()
        if result is None:
            raise FeaturesNotAvailableError(
                f"No hay features pre-calculadas para el partido {game_id} "
                f"en {self.ml_schema}.ml_ready_games. Ejecutar el ETL "
                f"build_features.py o esperar a que el partido sea procesado."
            )
        row_dict = dict(result)
        self._cache[gid] = row_dict
        return row_dict

    # ------------------------------------------------------------------
    # Construcción del vector X listo para el modelo
    # ------------------------------------------------------------------

    def build_feature_vector(
        self,
        game_id: int,
        feature_set: str = "v2",
    ) -> np.ndarray:
        """Devuelve un array (1, N) con las features ordenadas según el modelo.

        Args:
            game_id:      identificador del partido en ml.ml_ready_games.
            feature_set:  "v1" (21 features) o "v2" (33 features). Debe
                          coincidir con la versión del modelo activo.

        Returns:
            ndarray de shape (1, N) listo para `model.predict_full(X)`.
            Los valores NaN se conservan tal cual; el SimpleImputer interno
            del pipeline del modelo los rellenará con la mediana de
            entrenamiento.
        """
        if feature_set not in FEATURE_SETS:
            raise UnknownFeatureSetError(
                f"feature_set debe ser 'v1' o 'v2', recibido '{feature_set}'"
            )

        features = self.get_features_for_game(game_id)
        columns = FEATURE_SETS[feature_set]

        # Las columnas que no estén en el dict se imputarán como NaN — el
        # SimpleImputer del pipeline las reemplaza por la mediana de entrenamiento.
        row = [
            float(features[col]) if features.get(col) is not None else np.nan
            for col in columns
        ]
        X = np.array([row], dtype=float)
        assert X.shape == (1, len(columns)), (
            f"Vector mal formado: shape={X.shape}, esperado (1, {len(columns)})"
        )
        return X

    # ------------------------------------------------------------------
    # Utilidades adicionales (auditoría / debugging)
    # ------------------------------------------------------------------

    def get_features_summary(self, game_id: int, feature_set: str = "v2") -> Dict[str, Any]:
        """Devuelve el dict completo de features que se pasaron al modelo,
        listo para persistir en sys.predictions.features (auditoría)."""
        features = self.get_features_for_game(game_id)
        columns = FEATURE_SETS[feature_set]
        used = {
            col: (float(features[col]) if features.get(col) is not None else None)
            for col in columns
        }
        return {
            "feature_set": feature_set,
            "n_features": len(columns),
            "values": used,
            "missing_count": sum(1 for v in used.values() if v is None),
        }
