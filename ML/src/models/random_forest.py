"""
Modelo RandomForest con calibración de probabilidades.

Envuelve RandomForestClassifier de scikit-learn con CalibratedClassifierCV
(método isotonic) para garantizar que las probabilidades de salida sean
estadísticamente calibradas, requisito explícito del model spec.
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer


# Hiperparámetros por defecto — deterministas para reproducibilidad
DEFAULT_PARAMS = {
    "n_estimators": 300,
    "max_depth": 8,
    "min_samples_split": 20,
    "min_samples_leaf": 10,
    "max_features": "sqrt",
    "class_weight": "balanced",
    "random_state": 42,
    "n_jobs": -1,
}


class NBARandomForest:
    """
    Clasificador binario calibrado para predicción de home_win.

    Pipeline interno:
        SimpleImputer (median) → StandardScaler → RandomForest → Calibración isotónica

    La calibración con cv=5 y method='isotonic' reduce el overconfidence
    típico de Random Forest y minimiza el Calibration Error (ECE).
    """

    def __init__(self, params: dict = None):
        self.params = params or DEFAULT_PARAMS
        self.pipeline = None
        self.feature_names = None
        self.feature_importances_ = None
        self.is_fitted = False

    def build_pipeline(self) -> Pipeline:
        rf = RandomForestClassifier(**self.params)
        calibrated = CalibratedClassifierCV(
            estimator=rf,
            method="isotonic",
            cv=5,
        )
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", calibrated),
        ])

    def fit(self, X, y, feature_names: list = None):
        """Entrena el pipeline completo."""
        self.feature_names = feature_names or list(range(X.shape[1]))
        self.pipeline = self.build_pipeline()
        self.pipeline.fit(X, y)

        # Extraer importancias del RF interno (promedio de los estimadores calibrados)
        try:
            calibrated_model = self.pipeline.named_steps["model"]
            importances = np.mean([
                est.estimator.feature_importances_
                for est in calibrated_model.calibrated_classifiers_
            ], axis=0)
            self.feature_importances_ = dict(zip(self.feature_names, importances))
        except Exception:
            self.feature_importances_ = {}

        self.is_fitted = True
        return self

    def predict_proba(self, X) -> np.ndarray:
        """Retorna probabilidades [P(away_win), P(home_win)] para cada fila."""
        if not self.is_fitted:
            raise RuntimeError("El modelo no ha sido entrenado. Ejecutar .fit() primero.")
        return self.pipeline.predict_proba(X)

    def predict(self, X) -> np.ndarray:
        """Retorna clase predicha (0 o 1)."""
        proba = self.predict_proba(X)
        return (proba[:, 1] >= 0.5).astype(int)

    def predict_home_win_proba(self, X) -> np.ndarray:
        """Retorna solo P(home_win) como array 1D."""
        return self.predict_proba(X)[:, 1]

    def get_top_features(self, n: int = 10) -> list:
        """Retorna las n features más importantes ordenadas por importancia."""
        if not self.feature_importances_:
            return []
        sorted_feats = sorted(
            self.feature_importances_.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_feats[:n]
