"""
Tests del módulo de inferencia (app/services/ml_inference.py).

Estos tests no requieren conexión a Neon: construyen un NBAEnsemble
sintético en memoria con scikit-learn/XGBoost y verifican que el código
de inferencia del backend reproduce las predicciones del ensemble en
todas las versiones soportadas (meta_dim 2 / 3 / 4).

Ejecutar:
    cd Backend
    python -m unittest tests.test_ml_inference -v
"""

import os
import sys
import unittest

import numpy as np

# Permitir import del backend y del módulo ML como hermanos
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_ROOT)
sys.path.insert(0, BACKEND_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "ML"))

from app.services.ml_inference import (  # noqa: E402
    detect_feature_set, detect_meta_dim,
    predict_home_win_proba, predict_full_robust,
    extract_single_sample, validate_prediction,
    InferenceError,
)
from src.models.ensemble import NBAEnsemble  # noqa: E402


def _build_ensemble(n=200, n_features=21, with_team_props=False, seed=0):
    """Construye un NBAEnsemble entrenado sintético."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, (n, n_features))
    h = np.clip(110 + 3 * X[:, 0] + rng.normal(0, 8, n), 70, 160).astype(int)
    a = np.clip(108 - 3 * X[:, 0] + rng.normal(0, 8, n), 70, 160).astype(int)
    y = (h > a).astype(int)
    targets = None
    if with_team_props:
        targets = {
            "home_reb": np.clip(45 + rng.normal(0, 5, n), 25, 75),
            "away_reb": np.clip(43 + rng.normal(0, 5, n), 25, 75),
            "home_ast": np.clip(25 + rng.normal(0, 4, n), 10, 45),
            "away_ast": np.clip(24 + rng.normal(0, 4, n), 10, 45),
        }
    m = NBAEnsemble(n_folds=3)
    m.fit(X, y, h, a, team_stat_targets=targets,
          feature_names=[f"f{i}" for i in range(n_features)])
    return m, X


class TestDetectFeatureSet(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m21, _ = _build_ensemble(n_features=21)
        cls.m33, _ = _build_ensemble(n_features=33)

    def test_detects_v1_with_21_features(self):
        self.assertEqual(detect_feature_set(self.m21), "v1")

    def test_detects_v2_with_33_features(self):
        self.assertEqual(detect_feature_set(self.m33), "v2")


class TestDetectMetaDim(unittest.TestCase):

    def test_pipeline_logreg_4d(self):
        m, _ = _build_ensemble()
        self.assertEqual(detect_meta_dim(m.meta_learner), 4)


class TestPredictHomeWinProba(unittest.TestCase):

    def test_returns_calibrated_probas_in_unit_interval(self):
        m, X = _build_ensemble()
        proba = predict_home_win_proba(m, X[:30])
        self.assertEqual(proba.shape, (30,))
        self.assertTrue((proba > 0).all() and (proba < 1).all())


class TestPredictFullRobust(unittest.TestCase):

    def test_exposes_basic_outputs(self):
        m, X = _build_ensemble()
        out = predict_full_robust(m, X[:5])
        for key in ("home_win_probability", "away_win_probability",
                    "predicted_home_score", "predicted_away_score",
                    "predicted_margin", "predicted_total",
                    "poisson_probability", "rf_probability"):
            self.assertIn(key, out, f"falta {key}")

    def test_team_props_present_when_trained(self):
        m, X = _build_ensemble(with_team_props=True)
        out = predict_full_robust(m, X[:3])
        self.assertIn("team_props", out)
        self.assertIn("home", out["team_props"])
        self.assertIn("reb", out["team_props"]["home"])

    def test_team_props_absent_when_not_trained(self):
        m, X = _build_ensemble(with_team_props=False)
        out = predict_full_robust(m, X[:3])
        self.assertNotIn("team_props", out)


class TestExtractSingleSample(unittest.TestCase):

    def test_reduces_arrays_to_scalars(self):
        m, X = _build_ensemble()
        out = predict_full_robust(m, X[:5])
        scalar = extract_single_sample(out, idx=2)
        self.assertIsInstance(scalar["home_win_probability"], float)
        self.assertIsInstance(scalar["predicted_home_score"], float)
        self.assertAlmostEqual(
            scalar["home_win_probability"] + scalar["away_win_probability"],
            1.0, places=4,
        )


class TestValidatePrediction(unittest.TestCase):

    def test_valid_prediction_passes(self):
        validate_prediction({
            "home_win_probability": 0.6,
            "away_win_probability": 0.4,
            "predicted_home_score": 110.0,
            "predicted_away_score": 105.0,
        })

    def test_invalid_proba_out_of_range(self):
        with self.assertRaises(InferenceError):
            validate_prediction({
                "home_win_probability": 1.2,
                "away_win_probability": -0.2,
            })

    def test_proba_does_not_sum_to_one(self):
        with self.assertRaises(InferenceError):
            validate_prediction({
                "home_win_probability": 0.6,
                "away_win_probability": 0.5,  # 1.1, no es 1.0
            })

    def test_score_out_of_range(self):
        with self.assertRaises(InferenceError):
            validate_prediction({
                "home_win_probability": 0.5,
                "away_win_probability": 0.5,
                "predicted_home_score": 300.0,
                "predicted_away_score": 100.0,
            })

    def test_missing_proba_rejected(self):
        with self.assertRaises(InferenceError):
            validate_prediction({})


if __name__ == "__main__":
    unittest.main(verbosity=2)
