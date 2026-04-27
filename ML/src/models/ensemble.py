"""
Ensemble de apilamiento (Stacking) para predicción NBA — v2.1.2.

Diferencia con v2.1.0:
    El Bivariate Poisson NO entra al meta-learner como una probabilidad.
    Entra como features estructurales (μ_diff y σ_diff) que aportan
    "magnitud + incertidumbre" sin imponer una decisión probabilística.

Razón del cambio (v2.1.0 → v2.1.2):
    En v2.1.0 metíamos `[rf_proba, score_diff, poisson_proba]` al
    LogisticRegression. Eso mezclaba dos probabilidades con regímenes
    de calibración incompatibles:
      - rf_proba: discriminativa, calibrada vía CalibratedClassifierCV.
      - poisson_proba: estructural, derivada de E[D]/σ — tendencia a
        extremos, no optimizada para classification log-loss.
    El meta-learner aprendía a confiar en la señal más extrema
    (Poisson) y la isotónica 1D no compensaba el sesgo. Resultado:
    overconfidence en bins [0.7, 0.9) y ECE 0.084 en NBA real.

Arquitectura v2.1.2:
    Capa 1 — RandomForest      → rf_proba ∈ [0, 1]            (calibrada)
    Capa 1 — XGBoost           → score_diff (puntos)          (regresivo)
    Capa 1 — Bivariate Poisson → mu_diff, sigma_diff (puntos) (estructural)
    Capa 2 — StandardScaler + LogRegression → P(home_win)
    Capa 3 — IsotonicRegression sobre OOF (anti-leakage)

OOF stacking temporal (sin cambios desde v2.1.0):
    K=5 folds temporales; cada fold reentrena los 3 base learners en los
    k-1 folds previos y predice el fold k. La isotónica se ajusta sobre
    las OOF predictions (unbiased) y los base learners se reentrenan al
    final sobre el dataset completo para la predicción en producción.
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from .random_forest import NBARandomForest
from .xgboost_model import NBAXGBoost
from .poisson_model import NBABivariatePoisson
from .margin_model import NBAMarginModel
from .total_model import NBATotalModel


# Dimensión del vector de meta-features de Capa 2.
# v2.1.0 — [rf_proba, score_diff, poisson_proba]                        (3D)
# v2.1.2 — [rf_proba, score_diff, poisson_mu_diff, poisson_sigma_diff]  (4D)
META_FEATURE_DIM = 4


class NBAEnsemble:
    """
    Meta-modelo de stacking con OOF temporal y calibración isotónica.

    El meta-learner (LogisticRegression) recibe:
        - rf_proba:      P(home_win) del RandomForest calibrado
        - score_diff:    home_score_pred - away_score_pred del XGBoost
        - poisson_proba: P(home_win) del Bivariate Poisson (v2.1.0)

    OOF stacking elimina el leakage de calibración porque las predicciones
    del meta-learner en training son genuinamente out-of-fold (el modelo
    nunca vio esos partidos al hacer la predicción).
    """

    def __init__(
        self,
        rf_model: NBARandomForest = None,
        xgb_model: NBAXGBoost = None,
        poisson_model: NBABivariatePoisson = None,
        margin_model: NBAMarginModel = None,
        total_model: NBATotalModel = None,
        n_folds: int = 5,
    ):
        self.rf = rf_model or NBARandomForest()
        self.xgb = xgb_model or NBAXGBoost()
        self.poisson = poisson_model or NBABivariatePoisson()
        self.margin_model = margin_model or NBAMarginModel()
        self.total_model = total_model or NBATotalModel()
        # v2.1.2: meta-learner como Pipeline(StandardScaler → LogReg).
        # Las 4 meta-features viven en escalas distintas:
        #   rf_proba ∈ [0, 1], score_diff ∈ [-25, 25],
        #   mu_diff ∈ [-25, 25], sigma_diff ∈ [10, 18].
        # Sin estandarización, score_diff/mu_diff dominan por mayor varianza
        # absoluta y aplastan a rf_proba en la regresión logística.
        # C=0.1 mantiene la regularización L2 fuerte para reducir
        # overconfidence (lección de v2.1.0).
        self.meta_learner = Pipeline([
            ("scaler", StandardScaler()),
            ("logreg", LogisticRegression(C=0.1, random_state=42, max_iter=1000)),
        ])
        self.calibrator = None          # IsotonicRegression sobre OOF predictions
        self.n_folds = n_folds
        self.is_fitted = False
        self.feature_names = None

    def _poisson_meta_signals(self, X):
        """Devuelve (mu_diff, sigma_diff) del Bivariate Poisson como
        features estructurales para el meta-learner.

        - mu_diff    = E[X1 - X2] = λ1 - λ2          (ventaja esperada)
        - sigma_diff = √Var(X1 - X2) = √(λ1 + λ2)    (incertidumbre)

        Estas son cantidades en la escala original de puntos NBA. NO se
        transforman a probabilidad antes de entrar al meta-learner para
        evitar el problema de calibración mixta de v2.1.0.
        """
        lambdas = self.poisson.predict_lambdas(X)
        mu_diff = lambdas["lambda1"] - lambdas["lambda2"]
        sigma_diff = np.sqrt(np.clip(lambdas["lambda1"] + lambdas["lambda2"], 1e-9, None))
        return mu_diff, sigma_diff

    def _build_meta_features(self, X) -> np.ndarray:
        """Construye la matriz de meta-features para el meta-learner.

        v2.1.2: 4D = [rf_proba, score_diff, poisson_mu_diff, poisson_sigma_diff].

        Razón: el Poisson aporta *estructura* (magnitud esperada e
        incertidumbre) en lugar de una decisión probabilística rival.
        El StandardScaler interno del Pipeline deja a las 4 columnas en
        la misma escala antes del LogReg.
        """
        rf_proba = self.rf.predict_home_win_proba(X).reshape(-1, 1)
        score_diff = self.xgb.predict_score_diff(X).reshape(-1, 1)
        mu_diff, sigma_diff = self._poisson_meta_signals(X)
        return np.hstack([
            rf_proba,
            score_diff,
            mu_diff.reshape(-1, 1),
            sigma_diff.reshape(-1, 1),
        ])

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
        # v2.1.2: meta-features = [rf_proba, score_diff, poisson_mu_diff, poisson_sigma_diff]
        oof_meta_X = np.zeros((n, META_FEATURE_DIM))
        fold_size = n // self.n_folds

        print(f"  OOF stacking ({self.n_folds} folds temporales, "
              f"{META_FEATURE_DIM} meta-features: "
              f"rf_proba | xgb_score_diff | poisson_mu_diff | poisson_sigma_diff)...")
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

            rf_fold      = NBARandomForest()
            xgb_fold     = NBAXGBoost()
            poisson_fold = NBABivariatePoisson()
            rf_fold.fit(X_fold_tr, y_fold_tr, feature_names=feature_names)
            xgb_fold.fit(X_fold_tr, yh_fold_tr, ya_fold_tr)
            poisson_fold.fit(X_fold_tr, yh_fold_tr, ya_fold_tr,
                             feature_names=feature_names)

            # rf_proba ∈ [0, 1]
            oof_meta_X[val_start:val_end, 0] = rf_fold.predict_home_win_proba(X_fold_val)
            # XGBoost score_diff (puntos)
            oof_meta_X[val_start:val_end, 1] = xgb_fold.predict_score_diff(X_fold_val)
            # Bivariate Poisson como features estructurales (NO probabilidad)
            poisson_lambdas = poisson_fold.predict_lambdas(X_fold_val)
            oof_meta_X[val_start:val_end, 2] = (
                poisson_lambdas["lambda1"] - poisson_lambdas["lambda2"]
            )
            oof_meta_X[val_start:val_end, 3] = np.sqrt(np.clip(
                poisson_lambdas["lambda1"] + poisson_lambdas["lambda2"], 1e-9, None
            ))
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
        self.poisson.fit(X, y_home_score, y_away_score, feature_names=feature_names)
        print(f"  [Poisson] λ3 estimado: {self.poisson.lambda3_:.4f}")

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
          - home_win_probability / away_win_probability (calibrada)
          - predicted_margin (modelo dedicado)
          - predicted_total (modelo dedicado)
          - predicted_home_score / predicted_away_score (XGBoost legacy)
          - rf_probability (señal base del RF)
          - poisson_probability (señal del Bivariate Poisson, v2.1.0)
          - poisson_lambda1 / lambda2 / lambda3 (parámetros Karlis-Ntzoufras)
          - poisson_home_score / poisson_away_score (E[X1], E[X2])
        """
        home_proba = self.predict_home_win_proba(X)
        home_score, away_score = self.xgb.predict_scores(X)
        rf_proba = self.rf.predict_home_win_proba(X)
        margin = self.margin_model.predict_margin(X) if self.margin_model.is_fitted else home_score - away_score
        total = self.total_model.predict_total(X) if self.total_model.is_fitted else home_score + away_score

        # Señales del Bivariate Poisson (v2.1.0)
        poisson_proba = self.poisson.predict_home_win_proba(X)
        poisson_lambdas = self.poisson.predict_lambdas(X)

        return {
            "home_win_probability": home_proba,
            "away_win_probability": 1.0 - home_proba,
            "predicted_margin": margin,
            "predicted_total": total,
            "predicted_home_score": home_score,
            "predicted_away_score": away_score,
            "score_diff": home_score - away_score,
            "rf_probability": rf_proba,
            "poisson_probability": poisson_proba,
            "poisson_lambda1": poisson_lambdas["lambda1"],
            "poisson_lambda2": poisson_lambdas["lambda2"],
            "poisson_lambda3": poisson_lambdas["lambda3"],
            "poisson_home_score": poisson_lambdas["mu_home"],
            "poisson_away_score": poisson_lambdas["mu_away"],
        }
