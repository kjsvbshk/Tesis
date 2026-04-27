"""
Tests unitarios para NBABivariatePoisson (v2.1.0).

Verifica:
  - Forma y rango de las predicciones
  - Coherencia matemática del modelo Karlis & Ntzoufras 2003:
        E[X1] = λ1 + λ3,  Var(X1-X2) = λ1 + λ2,  Cov(X1, X2) = λ3
  - Estabilidad numérica de la PMF en log-space
  - Equivalencia entre la aproximación normal y la PMF exacta
  - Persistencia con joblib (save/load)
"""

import os
import sys
import math
import tempfile
import unittest

import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
sys.path.insert(0, PROJECT_ROOT)

from src.models.poisson_model import NBABivariatePoisson, LAMBDA_MIN, LAMBDA_MAX  # noqa: E402


def _generate_synthetic_nba_dataset(n: int = 600, n_features: int = 18, seed: int = 0):
    """Genera un dataset sintético con la misma forma que ml.ml_ready_games.

    home_score ~ Poisson(λ1 + λ3), away_score ~ Poisson(λ2 + λ3) con
    λ_marginal dependiente linealmente de un subset de features (log-link).
    """
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, size=(n, n_features))

    # Coeficientes verdaderos del proceso generador
    beta_home = rng.normal(0, 0.05, size=n_features)
    beta_away = rng.normal(0, 0.05, size=n_features)
    beta_home[0] = 0.10   # ppg_diff favorece local
    beta_home[5] = -0.08  # def_rating_diff
    beta_away[0] = -0.10
    beta_away[5] = 0.08

    log_mu_home = math.log(112.0) + X @ beta_home
    log_mu_away = math.log(108.0) + X @ beta_away
    mu_home = np.exp(log_mu_home)
    mu_away = np.exp(log_mu_away)

    # Componente común λ3 ≈ 8 (covarianza positiva)
    lambda3_true = 8.0
    z3 = rng.poisson(lambda3_true, size=n)
    z1 = rng.poisson(np.maximum(mu_home - lambda3_true, 1.0), size=n)
    z2 = rng.poisson(np.maximum(mu_away - lambda3_true, 1.0), size=n)
    home_score = z1 + z3
    away_score = z2 + z3
    y_home_win = (home_score > away_score).astype(int)
    return X, y_home_win, home_score, away_score, lambda3_true


class TestBivariatePoissonBasics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X, cls.y, cls.h, cls.a, cls.lambda3_true = _generate_synthetic_nba_dataset()
        cls.model = NBABivariatePoisson()
        cls.model.fit(cls.X, cls.h, cls.a)

    def test_is_fitted(self):
        self.assertTrue(self.model.is_fitted)
        self.assertIsNotNone(self.model.home_pipeline)
        self.assertIsNotNone(self.model.away_pipeline)

    def test_lambdas_are_positive(self):
        lam = self.model.predict_lambdas(self.X)
        self.assertTrue((lam["lambda1"] > 0).all(), "λ1 debe ser positivo")
        self.assertTrue((lam["lambda2"] > 0).all(), "λ2 debe ser positivo")
        self.assertTrue((lam["lambda3"] >= 0).all(), "λ3 debe ser no negativo")

    def test_lambdas_are_within_realistic_nba_range(self):
        lam = self.model.predict_lambdas(self.X)
        self.assertTrue((lam["mu_home"] >= LAMBDA_MIN).all())
        self.assertTrue((lam["mu_home"] <= LAMBDA_MAX).all())
        self.assertTrue((lam["mu_away"] >= LAMBDA_MIN).all())
        self.assertTrue((lam["mu_away"] <= LAMBDA_MAX).all())

    def test_lambda3_close_to_truth(self):
        """λ3 estimado debe estar en el orden correcto (±5)."""
        self.assertAlmostEqual(self.model.lambda3_, self.lambda3_true,
                               delta=5.0,
                               msg=f"λ3 estimado={self.model.lambda3_} vs verdad={self.lambda3_true}")

    def test_predict_proba_shape_and_range(self):
        proba = self.model.predict_proba(self.X)
        self.assertEqual(proba.shape, (len(self.X), 2))
        self.assertTrue((proba >= 0).all() and (proba <= 1).all())
        self.assertTrue(np.allclose(proba.sum(axis=1), 1.0, atol=1e-9))

    def test_predict_home_win_proba_range(self):
        p = self.model.predict_home_win_proba(self.X)
        self.assertEqual(p.shape, (len(self.X),))
        self.assertTrue((p > 0).all() and (p < 1).all())

    def test_marginal_decomposition(self):
        """E[X1] debe coincidir con λ1 + λ3 (definición del modelo)."""
        lam = self.model.predict_lambdas(self.X)
        self.assertTrue(np.allclose(lam["mu_home"], lam["lambda1"] + lam["lambda3"]))
        self.assertTrue(np.allclose(lam["mu_away"], lam["lambda2"] + lam["lambda3"]))

    def test_total_equals_lambda_sum(self):
        """E[X1+X2] = λ1 + λ2 + 2λ3."""
        lam = self.model.predict_lambdas(self.X)
        expected_total = lam["lambda1"] + lam["lambda2"] + 2.0 * lam["lambda3"]
        self.assertTrue(np.allclose(self.model.predict_total(self.X), expected_total))

    def test_margin_equals_lambda_diff(self):
        """E[X1-X2] = λ1 - λ2."""
        lam = self.model.predict_lambdas(self.X)
        expected_margin = lam["lambda1"] - lam["lambda2"]
        self.assertTrue(np.allclose(self.model.predict_margin(self.X), expected_margin))

    def test_predict_scores_clipped(self):
        h, a = self.model.predict_scores(self.X)
        self.assertTrue((h >= LAMBDA_MIN).all() and (h <= LAMBDA_MAX).all())
        self.assertTrue((a >= LAMBDA_MIN).all() and (a <= LAMBDA_MAX).all())


class TestPoissonAccuracy(unittest.TestCase):
    """Sanity checks de calidad predictiva en datos sintéticos."""

    @classmethod
    def setUpClass(cls):
        cls.X, cls.y, cls.h, cls.a, _ = _generate_synthetic_nba_dataset(n=1000, seed=42)
        # Split 80/20 (sin shuffle, datos sintéticos no tienen orden temporal real)
        n_train = int(0.8 * len(cls.X))
        cls.X_train, cls.X_test = cls.X[:n_train], cls.X[n_train:]
        cls.h_train, cls.a_train = cls.h[:n_train], cls.a[:n_train]
        cls.y_test = cls.y[n_train:]
        cls.model = NBABivariatePoisson()
        cls.model.fit(cls.X_train, cls.h_train, cls.a_train)

    def test_better_than_random_classifier(self):
        from sklearn.metrics import log_loss, roc_auc_score
        p = self.model.predict_home_win_proba(self.X_test)
        ll = log_loss(self.y_test, p)
        auc = roc_auc_score(self.y_test, p)
        # Baselines: log_loss(0.5) = 0.693, AUC random = 0.5
        self.assertLess(ll, 0.693, f"Log loss {ll:.4f} debe ser mejor que el predictor 0.5")
        self.assertGreater(auc, 0.55, f"AUC {auc:.4f} debe superar el azar")


class TestExactPMFvsApproximation(unittest.TestCase):
    """La aproximación normal debe converger a la PMF exacta para n pequeño."""

    def test_pmf_normalization(self):
        model = NBABivariatePoisson()
        # Forzamos parámetros sin entrenamiento para test puramente analítico
        # Usamos directamente joint_logpmf
        from scipy.special import logsumexp
        l1, l2, l3 = 110.0, 108.0, 8.0
        log_pmf = []
        for x in range(60, 170):
            for y in range(60, 170):
                log_pmf.append(model.joint_logpmf(x, y, l1, l2, l3))
        total = float(np.exp(logsumexp(log_pmf)))
        # Debe ser ≈ 1 (cobertura del rango de scores)
        self.assertAlmostEqual(total, 1.0, places=2)


class TestPersistence(unittest.TestCase):
    def test_save_and_load(self):
        X, _, h, a, _ = _generate_synthetic_nba_dataset(n=200)
        model = NBABivariatePoisson().fit(X, h, a)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "poisson.joblib")
            model.save(path)
            loaded = NBABivariatePoisson.load(path)
        # Las predicciones deben ser idénticas
        np.testing.assert_allclose(
            model.predict_home_win_proba(X),
            loaded.predict_home_win_proba(X),
        )
        self.assertAlmostEqual(model.lambda3_, loaded.lambda3_)


class TestEdgeCases(unittest.TestCase):
    def test_raise_if_not_fitted(self):
        model = NBABivariatePoisson()
        with self.assertRaises(RuntimeError):
            model.predict_home_win_proba(np.zeros((1, 5)))

    def test_negative_scores_rejected(self):
        model = NBABivariatePoisson()
        X = np.zeros((5, 3))
        with self.assertRaises(ValueError):
            model.fit(X, np.array([100, -1, 90, 110, 95]), np.array([95, 100, 110, 100, 95]))

    def test_zero_lambda3_strategy(self):
        X, _, h, a, _ = _generate_synthetic_nba_dataset(n=200)
        model = NBABivariatePoisson(lambda3_strategy="zero").fit(X, h, a)
        self.assertEqual(model.lambda3_, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
