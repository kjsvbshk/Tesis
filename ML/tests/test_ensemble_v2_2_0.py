"""
Smoke test del NBAEnsemble v2.2.0 — team-props (rebotes, asistencias, robos,
bloqueos, turnovers) por equipo.

Verifica que:
  - El ensemble entrena 10 NBAStatRegressor cuando recibe team_stat_targets.
  - predict_full expone "team_props" con sub-claves home/away.
  - Los valores caen dentro del rango realista NBA.
  - El joblib roundtrip preserva los stat models.
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

from src.models.ensemble import NBAEnsemble, TEAM_STAT_KINDS  # noqa: E402
from src.models.stat_regressor import NBAStatRegressor, DEFAULT_RANGES  # noqa: E402


def _make_dataset(n: int = 400, n_features: int = 18, seed: int = 11):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, size=(n, n_features))
    home_score = np.clip(110 + 4 * X[:, 0] + rng.normal(0, 8, size=n), 70, 160).astype(int)
    away_score = np.clip(108 - 4 * X[:, 0] + rng.normal(0, 8, size=n), 70, 160).astype(int)
    y = (home_score > away_score).astype(int)

    # Targets de team-props sintéticos en rangos realistas
    team_targets = {
        "home_reb": np.clip(45 + 5 * X[:, 0] + rng.normal(0, 6, n), 25, 75),
        "away_reb": np.clip(43 - 4 * X[:, 0] + rng.normal(0, 6, n), 25, 75),
        "home_ast": np.clip(25 + 3 * X[:, 1] + rng.normal(0, 5, n), 10, 45),
        "away_ast": np.clip(24 - 2 * X[:, 1] + rng.normal(0, 5, n), 10, 45),
        "home_blk": np.clip(5 + rng.normal(0, 2, n), 0, 18),
        "away_blk": np.clip(5 + rng.normal(0, 2, n), 0, 18),
        "home_stl": np.clip(8 + rng.normal(0, 2, n), 1, 20),
        "away_stl": np.clip(8 + rng.normal(0, 2, n), 1, 20),
        "home_to":  np.clip(13 + rng.normal(0, 3, n), 4, 25),
        "away_to":  np.clip(13 + rng.normal(0, 3, n), 4, 25),
    }
    return X, y, home_score, away_score, team_targets


class TestStatRegressor(unittest.TestCase):
    """Tests unitarios del NBAStatRegressor."""

    def test_fit_predict_within_clip_range(self):
        rng = np.random.default_rng(0)
        X = rng.normal(0, 1, (200, 5))
        y = np.clip(45 + 4 * X[:, 0] + rng.normal(0, 5, 200), 25, 75)
        model = NBAStatRegressor(target_name="home_reb").fit(X, y)
        preds = model.predict(X)
        self.assertEqual(preds.shape, (200,))
        self.assertTrue((preds >= DEFAULT_RANGES["reb"][0]).all())
        self.assertTrue((preds <= DEFAULT_RANGES["reb"][1]).all())

    def test_negative_target_rejected(self):
        X = np.zeros((10, 3))
        y = np.array([5.0, -1.0, 4.0, 3.0, 2.0, 1.0, 0.0, 7.0, 8.0, 6.0])
        with self.assertRaises(ValueError):
            NBAStatRegressor(target_name="home_blk").fit(X, y)

    def test_raise_if_not_fitted(self):
        m = NBAStatRegressor(target_name="home_reb")
        with self.assertRaises(RuntimeError):
            m.predict(np.zeros((1, 3)))


class TestEnsembleTeamProps(unittest.TestCase):
    """Smoke tests end-to-end del ensemble v2.2.0."""

    @classmethod
    def setUpClass(cls):
        cls.X, cls.y, cls.h, cls.a, cls.team_targets = _make_dataset()
        cls.feature_cols = [f"f_{i}" for i in range(cls.X.shape[1])]

    def test_fit_trains_all_team_stat_models(self):
        m = NBAEnsemble(n_folds=3)
        m.fit(self.X, self.y, self.h, self.a,
              team_stat_targets=self.team_targets,
              feature_names=self.feature_cols)
        self.assertEqual(len(m.team_stat_models), 10,
                         "Debió entrenar 10 stat models (5 stats × 2 sides)")
        for kind in TEAM_STAT_KINDS:
            for side in ("home", "away"):
                key = f"{side}_{kind}"
                self.assertIn(key, m.team_stat_models, f"Falta {key}")
                self.assertTrue(m.team_stat_models[key].is_fitted)

    def test_predict_full_exposes_team_props(self):
        m = NBAEnsemble(n_folds=3).fit(
            self.X, self.y, self.h, self.a,
            team_stat_targets=self.team_targets,
            feature_names=self.feature_cols,
        )
        out = m.predict_full(self.X[:30])
        self.assertIn("team_props", out)
        for side in ("home", "away"):
            for kind in TEAM_STAT_KINDS:
                self.assertIn(kind, out["team_props"][side])
                arr = out["team_props"][side][kind]
                self.assertEqual(arr.shape, (30,))

    def test_predict_full_without_team_stat_models(self):
        """Si no se entrena team_stat_targets, predict_full no expone team_props."""
        m = NBAEnsemble(n_folds=3).fit(self.X, self.y, self.h, self.a,
                                       feature_names=self.feature_cols)
        out = m.predict_full(self.X[:10])
        self.assertNotIn("team_props", out, "team_props no debe existir si no hay stat models")

    def test_joblib_roundtrip_preserves_team_props(self):
        m = NBAEnsemble(n_folds=3).fit(
            self.X, self.y, self.h, self.a,
            team_stat_targets=self.team_targets,
            feature_names=self.feature_cols,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.joblib")
            joblib.dump(m, path)
            loaded = joblib.load(path)
        self.assertEqual(len(loaded.team_stat_models), 10)
        out_orig = m.predict_full(self.X[:10])
        out_load = loaded.predict_full(self.X[:10])
        for side in ("home", "away"):
            for kind in TEAM_STAT_KINDS:
                np.testing.assert_allclose(
                    out_orig["team_props"][side][kind],
                    out_load["team_props"][side][kind],
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
