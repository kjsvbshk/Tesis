"""
Modelo XGBoost para regresión de puntuaciones (home_score, away_score).

Entrena dos regressores independientes: uno para puntos del equipo local
y otro para el visitante. Sus predicciones se usan como features auxiliares
en el ensemble y como outputs interpretativos del sistema.
"""

import numpy as np
from xgboost import XGBRegressor
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


DEFAULT_HOME_PARAMS = {
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

DEFAULT_AWAY_PARAMS = DEFAULT_HOME_PARAMS.copy()


class NBAXGBoost:
    """
    Regresor doble para predicción de puntuaciones NBA.

    Entrena un modelo para home_score y otro para away_score.
    La diferencia predicha (home - away) se usa como feature en el ensemble
    para enriquecer la estimación de probabilidad de victoria local.
    """

    def __init__(self, home_params: dict = None, away_params: dict = None):
        self.home_params = home_params or DEFAULT_HOME_PARAMS
        self.away_params = away_params or DEFAULT_AWAY_PARAMS
        self.home_pipeline = None
        self.away_pipeline = None
        self.is_fitted = False

    def _build_pipeline(self, params: dict) -> Pipeline:
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", XGBRegressor(**params)),
        ])

    def fit(self, X, y_home: np.ndarray, y_away: np.ndarray):
        """
        Entrena ambos regressores.

        Args:
            X: matriz de features
            y_home: puntuaciones reales del equipo local
            y_away: puntuaciones reales del equipo visitante
        """
        self.home_pipeline = self._build_pipeline(self.home_params)
        self.away_pipeline = self._build_pipeline(self.away_params)

        self.home_pipeline.fit(X, y_home)
        self.away_pipeline.fit(X, y_away)

        self.is_fitted = True
        return self

    def predict_scores(self, X) -> tuple:
        """
        Retorna (predicted_home_score, predicted_away_score) como arrays 1D.
        Los scores se clipean a un rango razonable [70, 160] puntos.
        """
        if not self.is_fitted:
            raise RuntimeError("El modelo no ha sido entrenado. Ejecutar .fit() primero.")
        home_pred = np.clip(self.home_pipeline.predict(X), 70, 160)
        away_pred = np.clip(self.away_pipeline.predict(X), 70, 160)
        return home_pred, away_pred

    def predict_score_diff(self, X) -> np.ndarray:
        """Retorna diferencia predicha (home_score - away_score)."""
        home_pred, away_pred = self.predict_scores(X)
        return home_pred - away_pred

    def predict_total(self, X) -> np.ndarray:
        """Retorna total de puntos predicho (home + away)."""
        home_pred, away_pred = self.predict_scores(X)
        return home_pred + away_pred
