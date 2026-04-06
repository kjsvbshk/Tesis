"""
Ensemble de apilamiento (Stacking) para predicción NBA.

Combina las salidas del RandomForest calibrado y del XGBoost regresor
en un meta-modelo (LogisticRegression) que produce la predicción final.

Arquitectura:
    Capa 1 — RandomForest  → P(home_win) calibrada
    Capa 1 — XGBoost       → score_diff predicho (home - away)
    Capa 2 — LogRegression → P_final(home_win) usando ambas salidas

Calibración con Out-Of-Fold (OOF) Stacking:
    Para evitar el leakage de calibración (meta-learner entrenado sobre los
    mismos datos de los que predice), se usa OOF stacking temporal:
      1. Dividir training en K=5 folds temporales (sin datos del futuro)
      2. Para cada fold k, entrenar RF+XGB en los k-1 folds anteriores
         → obtener predicciones en el fold k (out-of-fold)
      3. Construir el meta-training set concatenando todos los OOF predictions
      4. Entrenar meta-learner sobre el meta-training set completo (OOF)
      5. Aplicar isotonic regression calibration sobre OOF predictions
         (las OOF son unbiased → la calibración no tiene leakage)
      6. Re-entrenar RF+XGB en el dataset completo para la predicción final
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from .random_forest import NBARandomForest
from .xgboost_model import NBAXGBoost
from .margin_model import NBAMarginModel
from .total_model import NBATotalModel


class NBAEnsemble:
    """
    Meta-modelo de stacking con OOF temporal y calibración isotónica.

    El meta-learner (LogisticRegression) recibe:
        - rf_proba:   P(home_win) del RandomForest calibrado
        - score_diff: home_score_pred - away_score_pred del XGBoost

    OOF stacking elimina el leakage de calibración porque las predicciones
    del meta-learner en training son genuinamente out-of-fold (el modelo
    nunca vio esos partidos al hacer la predicción).
    """

    def __init__(
        self,
        rf_model: NBARandomForest = None,
        xgb_model: NBAXGBoost = None,
        margin_model: NBAMarginModel = None,
        total_model: NBATotalModel = None,
        n_folds: int = 5,
    ):
        self.rf = rf_model or NBARandomForest()
        self.xgb = xgb_model or NBAXGBoost()
        self.margin_model = margin_model or NBAMarginModel()
        self.total_model = total_model or NBATotalModel()
        self.meta_learner = LogisticRegression(C=0.5, random_state=42, max_iter=1000)
        self.calibrator = None          # IsotonicRegression sobre OOF predictions
        self.n_folds = n_folds
        self.is_fitted = False
        self.feature_names = None

    def _build_meta_features(self, X) -> np.ndarray:
        """Construye la matriz de features para el meta-learner."""
        rf_proba = self.rf.predict_home_win_proba(X).reshape(-1, 1)
        score_diff = self.xgb.predict_score_diff(X).reshape(-1, 1)
        return np.hstack([rf_proba, score_diff])

    def fit(self, X, y, y_home_score: np.ndarray, y_away_score: np.ndarray,
            y_margin: np.ndarray = None, y_total: np.ndarray = None,
            feature_names: list = None):
        """
        Entrena el ensemble con OOF temporal stacking:

        Etapa 1 (OOF): K folds temporales → meta-features out-of-fold.
        Etapa 2: Meta-learner entrenado sobre todos los OOF meta-features.
        Etapa 3: Isotonic regression calibration sobre OOF predictions.
        Etapa 4: Re-entrena RF+XGB sobre el dataset completo.
        Etapa 5: Entrena modelos dedicados de margen y total.

        Args:
            X:             matriz de features de entrenamiento (ordenada por fecha)
            y:             target binario (home_win)
            y_home_score:  puntuaciones reales del equipo local
            y_away_score:  puntuaciones reales del equipo visitante
            y_margin:      point_diff real (home - away), derivado si None
            y_total:       total real (home + away), derivado si None
            feature_names: nombres de las columnas (opcional)
        """
        self.feature_names = feature_names
        n = len(X)

        if y_margin is None:
            y_margin = y_home_score - y_away_score
        if y_total is None:
            y_total = y_home_score + y_away_score

        # Etapa 1 — OOF stacking temporal
        oof_meta_X = np.zeros((n, 2))   # [rf_proba, score_diff] para cada muestra
        fold_size = n // self.n_folds

        print(f"  OOF stacking ({self.n_folds} folds temporales)...")
        for k in range(self.n_folds):
            val_start = k * fold_size
            val_end   = (k + 1) * fold_size if k < self.n_folds - 1 else n

            train_mask = np.ones(n, dtype=bool)
            train_mask[val_start:val_end] = False

            X_fold_tr  = X[train_mask]
            y_fold_tr  = y[train_mask]
            yh_fold_tr = y_home_score[train_mask]
            ya_fold_tr = y_away_score[train_mask]
            X_fold_val = X[val_start:val_end]

            rf_fold  = NBARandomForest()
            xgb_fold = NBAXGBoost()
            rf_fold.fit(X_fold_tr, y_fold_tr, feature_names=feature_names)
            xgb_fold.fit(X_fold_tr, yh_fold_tr, ya_fold_tr)

            oof_meta_X[val_start:val_end, 0] = rf_fold.predict_home_win_proba(X_fold_val)
            oof_meta_X[val_start:val_end, 1] = xgb_fold.predict_score_diff(X_fold_val)
            print(f"    Fold {k+1}/{self.n_folds}: val [{val_start}, {val_end})")

        # Etapa 2 — meta-learner sobre OOF meta-features (sin leakage)
        self.meta_learner.fit(oof_meta_X, y)

        # Etapa 3 — isotonic calibration sobre OOF predictions (unbiased)
        oof_raw_proba = self.meta_learner.predict_proba(oof_meta_X)[:, 1]
        self.calibrator = IsotonicRegression(out_of_bounds="clip")
        self.calibrator.fit(oof_raw_proba, y)
        print(f"  [Calibración] Isotónica OOF ajustada ({n} muestras).")

        # Etapa 4 — re-entrenamiento de los modelos base sobre el dataset completo
        self.rf.fit(X, y, feature_names=feature_names)
        self.xgb.fit(X, y_home_score, y_away_score)

        # Etapa 5 — modelos dedicados de margen y total
        print("  Entrenando modelo de margen dedicado...")
        self.margin_model.fit(X, y_margin)
        print("  Entrenando modelo de total dedicado...")
        self.total_model.fit(X, y_total)

        self.is_fitted = True
        return self

    def predict_proba(self, X) -> np.ndarray:
        """
        Retorna [P(away_win), P(home_win)] con calibración isotónica aplicada.
        Si el calibrador no está disponible, usa el meta-learner directamente.
        """
        if not self.is_fitted:
            raise RuntimeError("El ensemble no ha sido entrenado. Ejecutar .fit() primero.")
        meta_X = self._build_meta_features(X)
        raw_proba = self.meta_learner.predict_proba(meta_X)[:, 1]

        if self.calibrator is not None:
            calibrated = self.calibrator.predict(raw_proba)
            calibrated = np.clip(calibrated, 1e-6, 1 - 1e-6)
            return np.column_stack([1.0 - calibrated, calibrated])

        return self.meta_learner.predict_proba(meta_X)

    def predict_home_win_proba(self, X) -> np.ndarray:
        """Retorna solo P(home_win) como array 1D."""
        return self.predict_proba(X)[:, 1]

    def predict(self, X) -> np.ndarray:
        """Retorna clase predicha (0 o 1)."""
        return (self.predict_home_win_proba(X) >= 0.5).astype(int)

    def predict_full(self, X) -> dict:
        """
        Retorna un diccionario con todas las salidas del ensemble:
          - home_win_probability / away_win_probability
          - predicted_margin (modelo dedicado)
          - predicted_total (modelo dedicado)
          - predicted_home_score / predicted_away_score (XGBoost legacy)
          - rf_probability (señal base del RF)
        """
        home_proba = self.predict_home_win_proba(X)
        home_score, away_score = self.xgb.predict_scores(X)
        rf_proba = self.rf.predict_home_win_proba(X)
        margin = self.margin_model.predict_margin(X) if self.margin_model.is_fitted else home_score - away_score
        total = self.total_model.predict_total(X) if self.total_model.is_fitted else home_score + away_score

        return {
            "home_win_probability": home_proba,
            "away_win_probability": 1.0 - home_proba,
            "predicted_margin": margin,
            "predicted_total": total,
            "predicted_home_score": home_score,
            "predicted_away_score": away_score,
            "score_diff": home_score - away_score,
            "rf_probability": rf_proba,
        }
