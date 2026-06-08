"""
Regresor genérico de estadísticas de equipo (team-level props) — v2.2.0.

Incorpora un XGBoost regressor con el mismo patrón que NBAMarginModel y
NBATotalModel, pero parametrizable para predecir cualquier estadística
agregada por equipo:
    rebotes, asistencias, robos, bloqueos, turnovers, etc.

Arquitectura:
    SimpleImputer(median) → XGBRegressor

Cada instancia se entrena contra un único target (e.g. `home_reb`,
`away_blk`). En el ensemble se mantiene un diccionario
`team_stat_models: Dict[str, NBAStatRegressor]` para gestionar los 10
regresores (5 stats × 2 equipos).

Razón de tener una clase aparte en lugar de reusar XGBRegressor directo:
  - Encapsula clipping a un rango razonable por stat (evita predicciones
    negativas o absurdas).
  - Persiste el nombre del target y el rango para facilitar joblib roundtrip.
  - Misma firma .fit/.predict que el resto de modelos del proyecto.
"""

from __future__ import annotations

import numpy as np
from xgboost import XGBRegressor
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


# Hiperparámetros por defecto (alineados con NBAMarginModel/NBATotalModel)
DEFAULT_PARAMS = {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 10,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
}


# Rangos realistas para clipear predicciones (evita valores absurdos)
# Basado en distribución empírica NBA temporada 2023-2026
DEFAULT_RANGES = {
    "reb":   (25.0, 75.0),    # rebotes totales por equipo
    "ast":   (10.0, 45.0),    # asistencias
    "stl":   (1.0,  20.0),    # robos
    "blk":   (0.0,  18.0),    # bloqueos
    "to":    (4.0,  25.0),    # turnovers
    "tov":   (4.0,  25.0),    # alias de turnovers
    "three_pm": (4.0, 30.0),  # triples convertidos (si se añade)
}


def _stat_kind(target_name: str) -> str:
    """Extrae la "clase" de stat desde un nombre como 'home_reb' → 'reb'."""
    for kind in DEFAULT_RANGES:
        if target_name.endswith("_" + kind):
            return kind
    return "reb"  # default


class NBAStatRegressor:
    """
    Regresor XGBoost para una estadística de equipo (rebotes, asistencias,
    robos, bloqueos, turnovers).

    Args:
        target_name: nombre del target (ej. "home_reb", "away_blk").
                     Se usa para inferir el rango razonable de salida.
        params:      hiperparámetros XGBoost; usa DEFAULT_PARAMS si None.
        clip_range:  (min, max) para clipear predicciones; usa
                     DEFAULT_RANGES[stat_kind] si None.
    """

    def __init__(self, target_name: str = "stat",
                 params: dict | None = None,
                 clip_range: tuple[float, float] | None = None,
                 min_valid_target: float | None = None):
        """
        Args:
            target_name: nombre del target (ej. "home_reb", "away_blk").
            params:      hiperparámetros XGBoost.
            clip_range:  (min, max) para clipear predicciones.
            min_valid_target: umbral mínimo absoluto para considerar un valor de
                target como "válido" durante el entrenamiento. Por defecto se
                usa el extremo inferior del clip_range (suposición: si el
                target real es menor que el clip mínimo, es porque proviene de
                un boxscore incompleto y debe excluirse del fit). Pasar 0.0
                desactiva el filtro.
        """
        self.target_name = target_name
        self.params = params or DEFAULT_PARAMS
        kind = _stat_kind(target_name)
        self.clip_range = clip_range or DEFAULT_RANGES.get(kind, (0.0, 200.0))
        self.min_valid_target = (
            min_valid_target if min_valid_target is not None else self.clip_range[0]
        )
        self.pipeline: Pipeline | None = None
        self.is_fitted: bool = False
        # Diagnóstico del último fit
        self.n_train: int = 0
        self.n_dropped: int = 0

    # ------------------------------------------------------------------
    # Entrenamiento
    # ------------------------------------------------------------------

    def fit(self, X, y: np.ndarray):
        """Entrena el regresor con saneamiento previo de targets.

        v2.2.1 — filtra internamente las filas con target inválido:
          - NaN
          - valores negativos
          - valores por debajo de `min_valid_target` (típicamente 0 o muy
            bajos provenientes de partidos sin boxscore completo)

        Si tras filtrar quedan < 50 muestras, levanta ValueError porque el
        regresor no puede aprender nada útil.

        Args:
            X:  matriz de features (n_samples, n_features).
            y:  vector con la stat real del partido.
        """
        y = np.asarray(y, dtype=float)
        X = np.asarray(X)

        # Identificar filas válidas
        valid_mask = ~np.isnan(y) & (y >= self.min_valid_target)
        n_total = len(y)
        n_dropped = int((~valid_mask).sum())
        n_valid = int(valid_mask.sum())

        if n_valid < 50:
            raise ValueError(
                f"{self.target_name}: solo {n_valid} muestras válidas "
                f"(de {n_total}, mínimo válido = {self.min_valid_target}). "
                f"Insuficiente para entrenar."
            )

        X_clean = X[valid_mask]
        y_clean = y[valid_mask]

        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", XGBRegressor(**self.params)),
        ])
        self.pipeline.fit(X_clean, y_clean)
        self.is_fitted = True
        self.n_train = n_valid
        self.n_dropped = n_dropped
        return self

    # ------------------------------------------------------------------
    # Predicción
    # ------------------------------------------------------------------

    def _check_fitted(self):
        if not self.is_fitted:
            raise RuntimeError(
                f"NBAStatRegressor[{self.target_name}] no ha sido entrenado. "
                "Llamar a .fit() primero."
            )

    def predict(self, X) -> np.ndarray:
        """Predicción clipeada al rango realista de la stat."""
        self._check_fitted()
        raw = self.pipeline.predict(X)
        lo, hi = self.clip_range
        return np.clip(raw, lo, hi)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def save(self, path: str):
        import joblib
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "NBAStatRegressor":
        import joblib
        return joblib.load(path)
