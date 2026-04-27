"""
Smoke test end-to-end del NBAEnsemble v2.1.2.

Verifica que:
  - El ensemble entrena con RF + XGBoost + Bivariate Poisson.
  - Los meta-features tienen 4 dimensiones:
      [rf_proba, score_diff, poisson_mu_diff, poisson_sigma_diff]
  - El meta-learner es un Pipeline(StandardScaler → LogReg).
  - predict_full sigue exponiendo poisson_probability como diagnóstico
    (aunque ya NO entra al meta-learner).
  - El joblib resultante puede ser recargado y produce las mismas predicciones
    (compatibilidad con prediction_service.py del Backend).
"""

import os
import sys
import tempfile
import unittest

import numpy as np
import joblib

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
sys.path.insert(0, PROJECT_ROOT)

from src.models.ensemble import NBAEnsemble, META_FEATURE_DIM  # noqa: E402


def _make_dataset(n: int = 500, n_features: int = 18, seed: int = 7):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, size=(n, n_features))
    home_score = np.clip(110 + 4 * X[:, 0] + rng.normal(0, 8, size=n), 70, 160).astype(int)
    away_score = np.clip(108 - 4 * X[:, 0] + rng.normal(0, 8, size=n), 70, 160).astype(int)
    y = (home_score > away_score).astype(int)
    return X, y, home_score, away_score


class TestEnsembleV212(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X, cls.y, cls.h, cls.a = _make_dataset()
        cls.feature_cols = [f"f_{i}" for i in range(cls.X.shape[1])]

    def test_meta_feature_dim_constant(self):
        self.assertEqual(
            META_FEATURE_DIM, 4,
            "v2.1.2 debe tener 4 meta-features "
            "[rf_proba, score_diff, poisson_mu_diff, poisson_sigma_diff]",
        )

    def test_meta_learner_is_pipeline_with_scaler(self):
        """v2.1.2: meta-learner debe estandarizar antes del LogReg."""
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression

        model = NBAEnsemble()
        self.assertIsInstance(model.meta_learner, Pipeline)
        steps = dict(model.meta_learner.named_steps)
        self.assertIn("scaler", steps)
        self.assertIn("logreg", steps)
        self.assertIsInstance(steps["scaler"], StandardScaler)
        self.assertIsInstance(steps["logreg"], LogisticRegression)

    def test_train_and_predict(self):
        model = NBAEnsemble(n_folds=3)  # menos folds para velocidad
        model.fit(self.X, self.y, self.h, self.a, feature_names=self.feature_cols)
        self.assertTrue(model.is_fitted)
        self.assertTrue(model.poisson.is_fitted, "Poisson debió ser entrenado")
        self.assertTrue(model.rf.is_fitted)
        self.assertTrue(model.xgb.is_fitted)
        self.assertTrue(model.margin_model.is_fitted)
        self.assertTrue(model.total_model.is_fitted)

        # Meta features deben tener 4 columnas
        meta_X = model._build_meta_features(self.X[:10])
        self.assertEqual(meta_X.shape, (10, META_FEATURE_DIM))

        # Sigma_diff (col 3) siempre debe ser positivo
        self.assertTrue((meta_X[:, 3] > 0).all(),
                        "poisson_sigma_diff debe ser estrictamente positivo")

        # Probabilidades calibradas
        proba = model.predict_proba(self.X)
        self.assertEqual(proba.shape, (len(self.X), 2))
        self.assertTrue((proba >= 0).all() and (proba <= 1).all())

    def test_predict_full_includes_poisson_signals(self):
        model = NBAEnsemble(n_folds=3).fit(
            self.X, self.y, self.h, self.a, feature_names=self.feature_cols
        )
        out = model.predict_full(self.X[:20])
        for key in (
            "home_win_probability",
            "away_win_probability",
            "predicted_margin",
            "predicted_total",
            "predicted_home_score",
            "predicted_away_score",
            "rf_probability",
            "poisson_probability",
            "poisson_lambda1",
            "poisson_lambda2",
            "poisson_lambda3",
            "poisson_home_score",
            "poisson_away_score",
        ):
            self.assertIn(key, out, f"Falta señal '{key}' en predict_full")
            self.assertEqual(len(out[key]), 20)

    def test_joblib_roundtrip_matches_prediction_service_pattern(self):
        """Replica cómo prediction_service.py carga el .joblib."""
        model = NBAEnsemble(n_folds=3).fit(
            self.X, self.y, self.h, self.a, feature_names=self.feature_cols
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "nba_prediction_model_v2.1.0.joblib")
            joblib.dump(model, path)
            loaded = joblib.load(path)
        np.testing.assert_allclose(
            model.predict_home_win_proba(self.X),
            loaded.predict_home_win_proba(self.X),
            rtol=1e-9,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
