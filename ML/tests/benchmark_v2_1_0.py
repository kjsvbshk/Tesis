"""
Benchmark end-to-end v2.1.0 sobre dataset sintético NBA-realista.

Compara:
  - Ensemble v1.6.0 (RF + XGBoost) — sin Poisson
  - Ensemble v2.1.0 (RF + XGBoost + Bivariate Poisson)
  - Bivariate Poisson aislado

Métricas: Log Loss, Brier, ROC-AUC, ECE, Accuracy, MAE-margen, MAE-total.

Nota: este benchmark valida que el código de v2.1.0 es funcional y mejora
señales en datos sintéticos. Las métricas reales contra Neon/ml_ready_games
las debe ejecutar el usuario en su máquina con `python -m src.training.train`.
"""

import os
import sys
import math

import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
sys.path.insert(0, PROJECT_ROOT)

from src.models.poisson_model import NBABivariatePoisson  # noqa: E402
from src.models.ensemble import NBAEnsemble  # noqa: E402
from src.evaluation.metrics import evaluate_classifier, evaluate_regressor  # noqa: E402


def make_realistic_nba_dataset(n=1500, n_features=18, seed=2024):
    """Dataset sintético NBA-realista con orden temporal."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, size=(n, n_features))

    # Coeficientes para log(λ_marginal). Algunos features informativos.
    beta_h = np.zeros(n_features)
    beta_a = np.zeros(n_features)
    beta_h[0] = 0.06    # ppg_diff favorece local
    beta_h[1] = 0.04    # net_rating_diff
    beta_h[5] = -0.05   # def_rating_diff (mayor defensa rival = menos puntos)
    beta_h[6] = 0.03    # reb rolling
    beta_a[0] = -0.06
    beta_a[1] = -0.04
    beta_a[5] = 0.05
    beta_a[6] = -0.03

    log_mu_h = math.log(112.0) + X @ beta_h
    log_mu_a = math.log(108.5) + X @ beta_a
    mu_h = np.exp(log_mu_h)
    mu_a = np.exp(log_mu_a)

    lambda3 = 8.0
    z3 = rng.poisson(lambda3, size=n)
    z1 = rng.poisson(np.maximum(mu_h - lambda3, 1.0), size=n)
    z2 = rng.poisson(np.maximum(mu_a - lambda3, 1.0), size=n)
    home_score = z1 + z3
    away_score = z2 + z3
    y = (home_score > away_score).astype(int)
    return X, y, home_score, away_score


def run():
    np.random.seed(0)
    X, y, h, a = make_realistic_nba_dataset(n=1500)
    n = len(X)
    n_train = int(0.8 * n)

    X_tr, X_te = X[:n_train], X[n_train:]
    y_tr, y_te = y[:n_train], y[n_train:]
    h_tr, h_te = h[:n_train], h[n_train:]
    a_tr, a_te = a[:n_train], a[n_train:]

    print(f"\nDataset: n_train={n_train}, n_test={n - n_train}, "
          f"home_win_rate={y.mean():.3f}, "
          f"avg_score=({h.mean():.1f}, {a.mean():.1f})")

    # 1) Bivariate Poisson aislado
    print("\n--- Bivariate Poisson aislado ---")
    poisson = NBABivariatePoisson().fit(X_tr, h_tr, a_tr)
    p_poisson = poisson.predict_home_win_proba(X_te)
    m1 = evaluate_classifier(y_te, p_poisson, label="poisson")
    print(f"  log_loss={m1['log_loss']}  brier={m1['brier_score']}  "
          f"auc={m1['roc_auc']}  ece={m1['ece']}  acc={m1['accuracy']}  "
          f"passes_all={m1['passes_all']}  λ3={poisson.lambda3_:.3f}")

    # 2) Ensemble v2.1.0 (RF + XGB + Poisson)
    print("\n--- Ensemble v2.1.0 (RF + XGB + Bivariate Poisson) ---")
    ens = NBAEnsemble(n_folds=5).fit(X_tr, y_tr, h_tr, a_tr,
                                     feature_names=[f"f{i}" for i in range(X.shape[1])])
    p_ens = ens.predict_home_win_proba(X_te)
    m2 = evaluate_classifier(y_te, p_ens, label="ensemble_v2_1_0")
    print(f"  log_loss={m2['log_loss']}  brier={m2['brier_score']}  "
          f"auc={m2['roc_auc']}  ece={m2['ece']}  acc={m2['accuracy']}  "
          f"passes_all={m2['passes_all']}")

    # MAE de margen y total con modelos dedicados
    full = ens.predict_full(X_te)
    margin_true = (h_te - a_te).astype(float)
    total_true = (h_te + a_te).astype(float)
    rm = evaluate_regressor(margin_true, full["predicted_margin"], label="margin")
    rt = evaluate_regressor(total_true, full["predicted_total"], label="total")
    print(f"  margin_mae={rm['mae']}  total_mae={rt['mae']}")

    # 3) Comparativa de señales (correlación entre Poisson y RF)
    rf_p = ens.rf.predict_home_win_proba(X_te)
    poisson_p_in_ens = ens.poisson.predict_home_win_proba(X_te)
    score_diff = ens.xgb.predict_score_diff(X_te)
    print(f"\n  corr(rf, poisson)        = {np.corrcoef(rf_p, poisson_p_in_ens)[0,1]:.3f}")
    print(f"  corr(rf, score_diff)     = {np.corrcoef(rf_p, score_diff)[0,1]:.3f}")
    print(f"  corr(poisson, score_diff) = {np.corrcoef(poisson_p_in_ens, score_diff)[0,1]:.3f}")

    print("\nBenchmark sintético completado.")


if __name__ == "__main__":
    run()
