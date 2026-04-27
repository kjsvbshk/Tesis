"""
Ablation study — ¿el Bivariate Poisson realmente aporta valor al ensemble?
                ¿el problema es feature-set o data drift?

Compara, sobre el MISMO test set, las siguientes variantes:

  1. RF solo                      (calibrado isotónicamente, baseline)
  2. RF + XGBoost (sin Poisson)   (≈ v1.6.0)
  3. RF + XGBoost + Poisson_proba (v2.1.0 — Poisson como decisión)
  4. RF + XGBoost + Poisson_features (v2.1.2 — Poisson como estructura)

Soporta dos feature sets para diagnosticar el drift v1.6.0 → ablation actual:

  --features v1    21 features originales de v1.6.0
  --features v2    33 features actuales (v2.0+)
  --features both  corre ambos consecutivamente y reporta lado a lado

Uso
----
    python -m tests.ablation_study                              # sintético
    python -m tests.ablation_study --neon --features v1         # 21 feats
    python -m tests.ablation_study --neon --features v2         # 33 feats
    python -m tests.ablation_study --neon --features both       # comparativa

NOTA: El sandbox de Cowork no tiene salida a Postgres, por eso el modo
sintético es el default. Para correrlo contra Neon, ejecutarlo en tu máquina
local con --neon.
"""

from __future__ import annotations

import os
import sys
import math
import argparse

import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
sys.path.insert(0, PROJECT_ROOT)

from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.isotonic import IsotonicRegression  # noqa: E402

from src.models.random_forest import NBARandomForest  # noqa: E402
from src.models.xgboost_model import NBAXGBoost  # noqa: E402
from src.models.poisson_model import NBABivariatePoisson  # noqa: E402
from src.evaluation.metrics import (  # noqa: E402
    evaluate_classifier, print_metrics_report,
)


# ---------------------------------------------------------------------------
# Feature sets — ORDEN IDÉNTICO al pipeline de entrenamiento (src/training/train.py)
# ---------------------------------------------------------------------------
#
# CRÍTICO: cualquier .joblib entrenado por train.py espera las columnas en
# el orden DIFF_FEATURES + INDIVIDUAL_FEATURES tal como están definidas allí.
# Re-importamos esas listas para evitar mismatches al cargar modelos previos.

from src.training.train import DIFF_FEATURES as _TRAIN_DIFF
from src.training.train import INDIVIDUAL_FEATURES as _TRAIN_INDIV

# Features añadidas en v2.0.0 (12 totales: 7 diff + 5 individual)
_V2_EXTRA_DIFF = {
    "efg_pct_diff", "tov_rate_diff",
    "oreb_pct_diff", "dreb_pct_diff",
    "elo_diff", "streak_diff", "home_away_split_diff",
}
_V2_EXTRA_INDIV = {
    "home_elo", "away_elo",
    "home_streak", "away_streak",
    "h2h_home_advantage",
}

# v1 (21 features): solo las del orden de train.py que NO son v2_extras.
V1_FEATURES = (
    [f for f in _TRAIN_DIFF if f not in _V2_EXTRA_DIFF]
    + [f for f in _TRAIN_INDIV if f not in _V2_EXTRA_INDIV]
)
# v2 (33 features): orden idéntico al pipeline de entrenamiento.
V2_FEATURES = list(_TRAIN_DIFF) + list(_TRAIN_INDIV)

assert len(V1_FEATURES) == 21, f"V1 debe tener 21 features, tiene {len(V1_FEATURES)}"
assert len(V2_FEATURES) == 33, f"V2 debe tener 33 features, tiene {len(V2_FEATURES)}"

FEATURE_SETS = {
    "v1": V1_FEATURES,
    "v2": V2_FEATURES,
}


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

def load_synthetic(n=2000, n_features=18, seed=2024):
    """Dataset sintético NBA-realista bajo el mismo proceso generador del
    benchmark del Poisson."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, size=(n, n_features))
    beta_h = np.zeros(n_features)
    beta_a = np.zeros(n_features)
    beta_h[0] = 0.06; beta_h[1] = 0.04; beta_h[5] = -0.05; beta_h[6] = 0.03
    beta_a[0] = -0.06; beta_a[1] = -0.04; beta_a[5] = 0.05; beta_a[6] = -0.03
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


def load_neon(feature_set: str = "v2"):
    """Carga ml.ml_ready_games desde Neon (mismo split temporal del pipeline real).

    Args:
        feature_set: "v1" → 21 features originales de v1.6.0,
                     "v2" → 33 features actuales (default).

    Returns:
        ((X_tr, y_tr, h_tr, a_tr), (X_te, y_te, h_te, a_te), feature_cols_used)
    """
    from src.training.train import load_ml_ready_games, build_feature_matrix, DATE_COL
    from src.evaluation.validation import temporal_train_test_split

    if feature_set not in FEATURE_SETS:
        raise ValueError(f"feature_set debe ser uno de {list(FEATURE_SETS.keys())}")
    requested = FEATURE_SETS[feature_set]

    df = load_ml_ready_games()
    X, y, all_feature_cols, df_clean = build_feature_matrix(df, use_odds=False)

    # Filtrar al feature set solicitado, manteniendo solo las que existen en la BD
    feature_cols = [c for c in requested if c in df_clean.columns]
    missing = [c for c in requested if c not in df_clean.columns]
    if missing:
        print(f"  ⚠ Features ausentes en BD ({len(missing)}): {missing}")
    print(f"  Feature set '{feature_set}': usando {len(feature_cols)}/{len(requested)} columnas.")

    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)
    score_h = next((c for c in ['home_pts', 'home_score'] if c in df_clean.columns), 'home_score')
    score_a = next((c for c in ['away_pts', 'away_score'] if c in df_clean.columns), 'away_score')

    X_tr = df_train[feature_cols].values
    y_tr = df_train["home_win"].values
    h_tr = df_train[score_h].fillna(df_train[score_h].median()).values
    a_tr = df_train[score_a].fillna(df_train[score_a].median()).values

    X_te = df_test[feature_cols].values
    y_te = df_test["home_win"].values
    h_te = df_test[score_h].fillna(df_test[score_h].median()).values
    a_te = df_test[score_a].fillna(df_test[score_a].median()).values
    return (X_tr, y_tr, h_tr, a_tr), (X_te, y_te, h_te, a_te), feature_cols


# ---------------------------------------------------------------------------
# Variantes del ensemble (con OOF temporal de K=5)
# ---------------------------------------------------------------------------

def _oof_temporal_indices(n, k):
    """Yields (train_mask, val_start, val_end) para cada uno de los k folds
    temporales contiguos."""
    fold_size = n // k
    for i in range(k):
        a = i * fold_size
        b = (i + 1) * fold_size if i < k - 1 else n
        mask = np.ones(n, dtype=bool)
        mask[a:b] = False
        yield mask, a, b


def _fit_meta(meta_X_oof, y, with_scaler: bool, C: float = 0.1):
    """Entrena meta-learner sobre OOF features y retorna (model, calibrator)."""
    if with_scaler:
        meta = Pipeline([
            ("scaler", StandardScaler()),
            ("logreg", LogisticRegression(C=C, random_state=42, max_iter=1000)),
        ])
    else:
        meta = LogisticRegression(C=C, random_state=42, max_iter=1000)
    meta.fit(meta_X_oof, y)
    raw = meta.predict_proba(meta_X_oof)[:, 1]
    cal = IsotonicRegression(out_of_bounds="clip").fit(raw, y)
    return meta, cal


def _meta_predict(meta, calibrator, meta_X):
    raw = meta.predict_proba(meta_X)[:, 1]
    return np.clip(calibrator.predict(raw), 1e-6, 1 - 1e-6)


def variant_rf_only(X_tr, y_tr, h_tr, a_tr, X_te, y_te, *_, **__):
    """Baseline 1 — RF solo (ya viene calibrado)."""
    rf = NBARandomForest().fit(X_tr, y_tr)
    return rf.predict_home_win_proba(X_te)


def variant_rf_xgb(X_tr, y_tr, h_tr, a_tr, X_te, y_te, *_, K=5, with_scaler=True):
    """Variante 2 — Stacking RF + XGBoost (≈ v1.6.0)."""
    n = len(X_tr)
    meta_X = np.zeros((n, 2))
    for mask, a, b in _oof_temporal_indices(n, K):
        rf_f = NBARandomForest().fit(X_tr[mask], y_tr[mask])
        xgb_f = NBAXGBoost().fit(X_tr[mask], h_tr[mask], a_tr[mask])
        meta_X[a:b, 0] = rf_f.predict_home_win_proba(X_tr[a:b])
        meta_X[a:b, 1] = xgb_f.predict_score_diff(X_tr[a:b])
    meta, cal = _fit_meta(meta_X, y_tr, with_scaler=with_scaler)
    rf = NBARandomForest().fit(X_tr, y_tr)
    xgb = NBAXGBoost().fit(X_tr, h_tr, a_tr)
    test_meta = np.column_stack([
        rf.predict_home_win_proba(X_te),
        xgb.predict_score_diff(X_te),
    ])
    return _meta_predict(meta, cal, test_meta)


def variant_rf_xgb_poisson_proba(X_tr, y_tr, h_tr, a_tr, X_te, y_te, *_, K=5, with_scaler=False):
    """Variante 3 — v2.1.0: Poisson como probabilidad."""
    n = len(X_tr)
    meta_X = np.zeros((n, 3))
    for mask, a, b in _oof_temporal_indices(n, K):
        rf_f = NBARandomForest().fit(X_tr[mask], y_tr[mask])
        xgb_f = NBAXGBoost().fit(X_tr[mask], h_tr[mask], a_tr[mask])
        po_f = NBABivariatePoisson().fit(X_tr[mask], h_tr[mask], a_tr[mask])
        meta_X[a:b, 0] = rf_f.predict_home_win_proba(X_tr[a:b])
        meta_X[a:b, 1] = xgb_f.predict_score_diff(X_tr[a:b])
        meta_X[a:b, 2] = po_f.predict_home_win_proba(X_tr[a:b])
    meta, cal = _fit_meta(meta_X, y_tr, with_scaler=with_scaler, C=0.5)
    rf = NBARandomForest().fit(X_tr, y_tr)
    xgb = NBAXGBoost().fit(X_tr, h_tr, a_tr)
    po = NBABivariatePoisson().fit(X_tr, h_tr, a_tr)
    test_meta = np.column_stack([
        rf.predict_home_win_proba(X_te),
        xgb.predict_score_diff(X_te),
        po.predict_home_win_proba(X_te),
    ])
    return _meta_predict(meta, cal, test_meta)


def variant_rf_xgb_poisson_features(X_tr, y_tr, h_tr, a_tr, X_te, y_te, *_, K=5, with_scaler=True):
    """Variante 4 — v2.1.2: Poisson como features estructurales."""
    n = len(X_tr)
    meta_X = np.zeros((n, 4))
    for mask, a, b in _oof_temporal_indices(n, K):
        rf_f = NBARandomForest().fit(X_tr[mask], y_tr[mask])
        xgb_f = NBAXGBoost().fit(X_tr[mask], h_tr[mask], a_tr[mask])
        po_f = NBABivariatePoisson().fit(X_tr[mask], h_tr[mask], a_tr[mask])
        meta_X[a:b, 0] = rf_f.predict_home_win_proba(X_tr[a:b])
        meta_X[a:b, 1] = xgb_f.predict_score_diff(X_tr[a:b])
        lam = po_f.predict_lambdas(X_tr[a:b])
        meta_X[a:b, 2] = lam["lambda1"] - lam["lambda2"]
        meta_X[a:b, 3] = np.sqrt(np.clip(lam["lambda1"] + lam["lambda2"], 1e-9, None))
    meta, cal = _fit_meta(meta_X, y_tr, with_scaler=with_scaler, C=0.1)
    rf = NBARandomForest().fit(X_tr, y_tr)
    xgb = NBAXGBoost().fit(X_tr, h_tr, a_tr)
    po = NBABivariatePoisson().fit(X_tr, h_tr, a_tr)
    lam_te = po.predict_lambdas(X_te)
    test_meta = np.column_stack([
        rf.predict_home_win_proba(X_te),
        xgb.predict_score_diff(X_te),
        lam_te["lambda1"] - lam_te["lambda2"],
        np.sqrt(np.clip(lam_te["lambda1"] + lam_te["lambda2"], 1e-9, None)),
    ])
    return _meta_predict(meta, cal, test_meta)


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def proba_distribution(proba, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    counts, _ = np.histogram(proba, bins=bins)
    return counts


def run_ablation(X_tr, y_tr, h_tr, a_tr, X_te, y_te, n_folds: int, label: str = ""):
    """Ejecuta las 4 variantes y devuelve dict con métricas y predicciones."""
    print(f"\n  n_train={len(X_tr)}, n_test={len(X_te)}, "
          f"n_features={X_tr.shape[1]}, "
          f"home_win_rate_train={y_tr.mean():.3f}"
          + (f"  [{label}]" if label else ""))

    variants = [
        ("RF solo                          ", variant_rf_only),
        ("RF + XGBoost (≈ v1.6.0)          ", variant_rf_xgb),
        ("RF + XGB + Poisson_proba (v2.1.0)", variant_rf_xgb_poisson_proba),
        ("RF + XGB + Poisson_feats (v2.1.2)", variant_rf_xgb_poisson_features),
    ]

    print(f"\n  {'Variante':<38} {'LogLoss':>8} {'Brier':>7} {'AUC':>6} "
          f"{'ECE':>7} {'Acc':>6}  Pasa")
    print("  " + "-" * 88)
    results = {}
    for name, fn in variants:
        p = fn(X_tr, y_tr, h_tr, a_tr, X_te, y_te, K=n_folds)
        m = evaluate_classifier(y_te, p, label=name.strip())
        results[name.strip()] = {"metrics": m, "proba": p}
        passes = "✓" if m["passes_all"] else "✗"
        print(f"  {name:<38} {m['log_loss']:>8.4f} {m['brier_score']:>7.4f} "
              f"{m['roc_auc']:>6.4f} {m['ece']:>7.4f} {m['accuracy']:>6.4f}  {passes}")

    print(f"\n  Distribución de predicciones por bin (n por intervalo):")
    print(f"  {'Variante':<38}  " + "  ".join(f"{b/10:.1f}" for b in range(10)))
    for name, payload in results.items():
        counts = proba_distribution(payload["proba"], n_bins=10)
        print(f"  {name:<38}  " + "  ".join(f"{c:>3d}" for c in counts))

    return results


def print_drift_diagnostic(results_v1: dict, results_v2: dict):
    """Imprime tabla side-by-side v1 vs v2 con la delta de Log Loss/ECE."""
    print("\n" + "=" * 90)
    print("DIAGNÓSTICO DE DRIFT — V1 (21 features) vs V2 (33 features)")
    print("=" * 90)
    header = (f"  {'Variante':<38}"
              f"{'LL_v1':>7} {'LL_v2':>7} {'ΔLL':>7}  "
              f"{'ECE_v1':>7} {'ECE_v2':>7} {'ΔECE':>7}")
    print(header)
    print("  " + "-" * 88)

    for name in results_v1.keys():
        m1 = results_v1[name]["metrics"]
        m2 = results_v2[name]["metrics"]
        d_ll = m2["log_loss"] - m1["log_loss"]
        d_ece = m2["ece"] - m1["ece"]
        print(f"  {name:<38}"
              f"{m1['log_loss']:>7.4f} {m2['log_loss']:>7.4f} {d_ll:>+7.4f}  "
              f"{m1['ece']:>7.4f} {m2['ece']:>7.4f} {d_ece:>+7.4f}")

    print("\n  Interpretación:")
    print("    Si ΔLL ≈ 0 y ΔECE ≈ 0   → no es feature drift; es DATA drift puro.")
    print("    Si ΔLL > 0 y ΔECE > 0   → las 12 features extra DEGRADAN el modelo.")
    print("    Si ΔLL < 0 y ΔECE < 0   → las 12 features extra mejoran y el problema es otro.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--neon", action="store_true",
                        help="Usar ml.ml_ready_games (requiere acceso a Neon)")
    parser.add_argument("--n-folds", type=int, default=5)
    parser.add_argument("--features", choices=["v1", "v2", "both"], default="v2",
                        help="Feature set (solo aplica a --neon). "
                             "v1=21 originales, v2=33 actuales, both=ambas comparadas.")
    args = parser.parse_args()

    if not args.neon:
        print("Cargando dataset sintético NBA-realista...")
        X, y, h, a = load_synthetic(n=2000)
        n_train = int(0.8 * len(X))
        X_tr, X_te = X[:n_train], X[n_train:]
        y_tr, y_te = y[:n_train], y[n_train:]
        h_tr, a_tr = h[:n_train], a[:n_train]
        run_ablation(X_tr, y_tr, h_tr, a_tr, X_te, y_te, args.n_folds,
                     label="sintético")
        print("\nLectura recomendada:")
        print("  - Si v2.1.2 mejora ECE vs v2.1.0 → la reformulación funciona.")
        print("  - Si v2.1.2 NO supera a 'RF + XGBoost' → el Poisson no aporta.")
        print("  - Si 'RF solo' tiene ECE comparable → el stacking entero es discutible.")
        return

    # Modo Neon
    if args.features == "both":
        print("\n" + "=" * 90)
        print("Cargando datos desde Neon — feature set V1 (21 features de v1.6.0)")
        print("=" * 90)
        (X_tr, y_tr, h_tr, a_tr), (X_te, y_te, _, _), feats_v1 = load_neon("v1")
        results_v1 = run_ablation(X_tr, y_tr, h_tr, a_tr, X_te, y_te, args.n_folds,
                                  label="v1: 21 features")

        print("\n" + "=" * 90)
        print("Cargando datos desde Neon — feature set V2 (33 features actuales)")
        print("=" * 90)
        (X_tr, y_tr, h_tr, a_tr), (X_te, y_te, _, _), feats_v2 = load_neon("v2")
        results_v2 = run_ablation(X_tr, y_tr, h_tr, a_tr, X_te, y_te, args.n_folds,
                                  label="v2: 33 features")

        print_drift_diagnostic(results_v1, results_v2)
    else:
        print("Cargando datos desde Neon...")
        (X_tr, y_tr, h_tr, a_tr), (X_te, y_te, _, _), _ = load_neon(args.features)
        run_ablation(X_tr, y_tr, h_tr, a_tr, X_te, y_te, args.n_folds,
                     label=f"feature_set={args.features}")


if __name__ == "__main__":
    main()
