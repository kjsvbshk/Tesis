"""
Modelo dedicado para predicción de margen de victoria (point_diff).

Optimiza directamente para home_score - away_score en lugar de
derivarlo de dos regresiones de scores independientes.
"""

import numpy as np
from xgboost import XGBRegressor
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


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


class NBAMarginModel:
    """
    Regresor XGBoost para margen de victoria (home_score - away_score).

    Rango típico NBA: [-40, +40]. Valores extremos se clipean a [-50, 50].
    """

    def __init__(self, params: dict = None):
        self.params = params or DEFAULT_PARAMS
        self.pipeline = None
        self.is_fitted = False

    def fit(self, X, y_margin: np.ndarray):
        """
        Entrena el regresor de margen.

        Args:
            X: matriz de features
            y_margin: point_diff real (home_score - away_score)
        """
        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", XGBRegressor(**self.params)),
        ])
        self.pipeline.fit(X, y_margin)
        self.is_fitted = True
        return self

    def predict_margin(self, X) -> np.ndarray:
        """Retorna margen predicho, clipeado a [-50, 50]."""
        if not self.is_fitted:
            raise RuntimeError("El modelo no ha sido entrenado. Ejecutar .fit() primero.")
        return np.clip(self.pipeline.predict(X), -50, 50)
