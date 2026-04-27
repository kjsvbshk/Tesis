"""
Evalúa cualquier modelo .joblib (v1.x, v2.1.x, etc.) contra el split temporal
actual de ml.ml_ready_games SIN re-entrenarlo.

Cierra el diagnóstico iniciado en el ablation_study:
  ¿v1.6.0 publicado todavía pasa criterios contra datos 2025-12 → 2026-03?
  ¿O también está degradado por data drift?

Robustez ante cambios entre versiones del NBAEnsemble:
  - El código actual espera atributos como `self.poisson` que el .joblib
    v1.6.0 no tiene → llamar `model.predict_home_win_proba(X)` directo
    fallaría con AttributeError.
  - Solución: reconstruir las predicciones desde los componentes individuales
    (model.rf, model.xgb, model.meta_learner, model.calibrator) infiriendo
    el formato esperado por meta_learner.coef_.shape.

Uso
----
    python -m scripts.evaluate_active_model                     # v1.6.0 (default)
    python -m scripts.evaluate_active_model --version v2.1.0
    python -m scripts.evaluate_active_model --version v1.6.0 --features v1
"""

from __future__ import annotations

import argparse
import os
import sys

import joblib
import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
sys.path.insert(0, PROJECT_ROOT)

from src.training.train import load_ml_ready_games, build_feature_matrix, DATE_COL  # noqa: E402
from src.evaluation.validation import temporal_train_test_split  # noqa: E402
from src.evaluation.metrics import evaluate_classifier  # noqa: E402
from tests.ablation_study import FEATURE_SETS  # noqa: E402


# Métricas oficiales del v1.6.0 publicado (referencia para diagnóstico de drift)
V160_PUBLISHED = {
    "log_loss": 0.6553,
    "brier_score": 0.2312,
    "roc_auc": 0.6542,
    "ece": 0.0363,
}


# ---------------------------------------------------------------------------
# Inferencia de la formulación del modelo
# ---------------------------------------------------------------------------

def detect_meta_dim(meta_learner) -> int:
    """Devuelve la dimensión esperada por el meta-learner (2/3/4)."""
    # meta_learner puede ser LogisticRegression directo (v1.x) o
    # Pipeline(StandardScaler → LogReg) (v2.1.2)
    if hasattr(meta_learner, "named_steps"):
        steps = meta_learner.named_steps
        for name, step in steps.items():
            if hasattr(step, "coef_"):
                return int(step.coef_.shape[1])
    if hasattr(meta_learner, "coef_"):
        return int(meta_learner.coef_.shape[1])
    raise RuntimeError("No pude inferir la dimensión del meta-learner.")


def detect_feature_set(model) -> str:
    """Devuelve 'v1' o 'v2' según la dimensión que espera el RF interno."""
    try:
        # NBARandomForest envuelve un Pipeline interno
        rf_pipeline = model.rf.pipeline
        # SimpleImputer guarda n_features_in_ tras fit
        n = rf_pipeline.named_steps["imputer"].n_features_in_
        if n == 21:
            return "v1"
        if n == 33:
            return "v2"
        raise RuntimeError(f"RF interno espera {n} features, no es 21 ni 33.")
    except Exception as e:
        raise RuntimeError(f"No pude inferir feature_set: {e}")


# ---------------------------------------------------------------------------
# Predicción robusta a versión
# ---------------------------------------------------------------------------

def predict_legacy(model, X: np.ndarray) -> np.ndarray:
    """Reconstruye P(home_win) desde los componentes del ensemble.

    Funciona con cualquier versión (v1.x / v2.1.0 / v2.1.2) sin asumir que
    el código actual de NBAEnsemble es compatible con el pickle cargado.
    """
    rf_proba = model.rf.predict_home_win_proba(X)
    score_diff = model.xgb.predict_score_diff(X)

    expected_dim = detect_meta_dim(model.meta_learner)

    cols = [rf_proba.reshape(-1, 1), score_diff.reshape(-1, 1)]

    if expected_dim == 2:
        # v1.x — solo RF + XGBoost
        pass
    elif expected_dim == 3:
        # v2.1.0 — añade poisson_proba
        if not hasattr(model, "poisson") or model.poisson is None:
            raise RuntimeError("meta_learner espera 3 cols pero no hay poisson en el modelo.")
        cols.append(model.poisson.predict_home_win_proba(X).reshape(-1, 1))
    elif expected_dim == 4:
        # v2.1.2 — añade mu_diff y sigma_diff
        if not hasattr(model, "poisson") or model.poisson is None:
            raise RuntimeError("meta_learner espera 4 cols pero no hay poisson en el modelo.")
        lam = model.poisson.predict_lambdas(X)
        mu_diff = (lam["lambda1"] - lam["lambda2"]).reshape(-1, 1)
        sigma_diff = np.sqrt(np.clip(lam["lambda1"] + lam["lambda2"], 1e-9, None)).reshape(-1, 1)
        cols.append(mu_diff)
        cols.append(sigma_diff)
    else:
        raise RuntimeError(f"Dimensión meta-learner inesperada: {expected_dim}")

    meta_X = np.hstack(cols)

    # meta_learner.predict_proba funciona en LogReg directo o Pipeline
    raw = model.meta_learner.predict_proba(meta_X)[:, 1]

    cal = getattr(model, "calibrator", None)
    if cal is not None:
        proba = cal.predict(raw)
        proba = np.clip(proba, 1e-6, 1.0 - 1e-6)
    else:
        proba = raw

    return proba


def proba_distribution(proba, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    counts, _ = np.histogram(proba, bins=bins)
    return counts


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def print_metric_row(name: str, published: float, current: float,
                     direction: str, threshold: float):
    """Imprime una fila comparando publicado vs actual con flag de criterio.

    direction: "<" → menor es mejor, ">" → mayor es mejor.
    """
    delta = current - published
    if direction == "<":
        passes = current < threshold
    else:
        passes = current > threshold
    flag = "✓" if passes else "✗"
    print(f"  {name:<14} {published:>8.4f}    {current:>8.4f}    {delta:>+7.4f}    {flag}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1.6.0",
                        help="Versión del modelo a evaluar")
    parser.add_argument("--features", choices=["v1", "v2", "auto"], default="auto",
                        help="Feature set; auto = inferir del modelo")
    parser.add_argument("--models-dir", default=None,
                        help="Override del directorio de modelos")
    args = parser.parse_args()

    models_dir = args.models_dir or os.path.join(PROJECT_ROOT, "models")
    model_path = os.path.join(models_dir, f"nba_prediction_model_{args.version}.joblib")

    if not os.path.exists(model_path):
        print(f"❌ Modelo no encontrado: {model_path}")
        # Listar modelos disponibles
        try:
            for f in sorted(os.listdir(models_dir)):
                if f.startswith("nba_prediction_model_") and f.endswith(".joblib"):
                    print(f"   disponible: {f}")
        except Exception:
            pass
        sys.exit(1)

    print(f"Cargando modelo: {model_path}")
    model = joblib.load(model_path)
    print(f"  Tipo: {type(model).__name__}")
    print(f"  Atributos relevantes: rf={hasattr(model, 'rf')}, "
          f"xgb={hasattr(model, 'xgb')}, "
          f"meta_learner={hasattr(model, 'meta_learner')}, "
          f"calibrator={hasattr(model, 'calibrator')}, "
          f"poisson={hasattr(model, 'poisson') and model.poisson is not None}")

    # Detectar formulación
    meta_dim = detect_meta_dim(model.meta_learner)
    print(f"  Meta-learner espera {meta_dim} features.")

    # Inferir feature set
    if args.features == "auto":
        feature_set = detect_feature_set(model)
        print(f"  Feature set inferido: {feature_set}")
    else:
        feature_set = args.features

    # Cargar y preparar datos (mismo proceso que ablation_study + train)
    print("\nCargando ml.ml_ready_games desde Neon...")
    df = load_ml_ready_games()
    X_all, y_all, _, df_clean = build_feature_matrix(df, use_odds=False)

    requested = FEATURE_SETS[feature_set]
    feature_cols = [c for c in requested if c in df_clean.columns]
    missing = [c for c in requested if c not in df_clean.columns]
    if missing:
        print(f"  ⚠ Features ausentes en BD ({len(missing)}): {missing}")
    print(f"  Feature set '{feature_set}': {len(feature_cols)}/{len(requested)} columnas.")

    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)
    X_test = df_test[feature_cols].values
    y_test = df_test["home_win"].values
    test_min = df_test[DATE_COL].min()
    test_max = df_test[DATE_COL].max()
    print(f"\n  Test set: n={len(X_test)} ({test_min} → {test_max})")

    # Predecir
    print(f"\nPrediciendo con {args.version} sobre el test set actual...")
    try:
        proba = predict_legacy(model, X_test)
    except Exception as e:
        print(f"  predict_legacy falló: {e}")
        print(f"  intentando model.predict_home_win_proba(X) directo...")
        proba = model.predict_home_win_proba(X_test)

    # Evaluar
    metrics = evaluate_classifier(y_test, proba, label=args.version)

    print(f"\n{'='*78}")
    print(f"  Diagnóstico de drift — {args.version}")
    print(f"  Test set: 2025-12 → 2026-03  (n={len(X_test)})")
    print(f"{'='*78}")
    print(f"  {'Métrica':<14} {'Publicado':>9}    {'Actual':>9}    {'Δ':>7}    Pasa")
    print("  " + "-" * 60)
    print_metric_row("Log Loss",   V160_PUBLISHED["log_loss"],    metrics["log_loss"],    "<", 0.68)
    print_metric_row("Brier",      V160_PUBLISHED["brier_score"], metrics["brier_score"], "<", 0.25)
    print_metric_row("ROC-AUC",    V160_PUBLISHED["roc_auc"],     metrics["roc_auc"],     ">", 0.55)
    print_metric_row("ECE",        V160_PUBLISHED["ece"],         metrics["ece"],         "<", 0.05)
    print(f"  {'Accuracy':<14} {'—':>9}    {metrics['accuracy']:>9.4f}")

    overall = "✓ PASA todos los criterios" if metrics["passes_all"] else "✗ NO pasa todos los criterios"
    print(f"\n  Veredicto: {overall}")

    # Distribución por bin
    counts = proba_distribution(proba, n_bins=10)
    print(f"\n  Distribución de predicciones por bin:")
    print("  " + "  ".join(f"{b/10:.1f}" for b in range(10)))
    print("  " + "  ".join(f"{c:>3d}" for c in counts))

    # Lectura del resultado
    print(f"\n{'='*78}")
    print("  Lectura")
    print(f"{'='*78}")
    delta_ll = metrics["log_loss"] - V160_PUBLISHED["log_loss"]
    delta_ece = metrics["ece"] - V160_PUBLISHED["ece"]
    if delta_ll > 0.02 or delta_ece > 0.02:
        print(f"  El modelo {args.version} sufre data drift: ΔLogLoss={delta_ll:+.4f}, "
              f"ΔECE={delta_ece:+.4f}.")
        print(f"  Las métricas publicadas reflejan el split antiguo, no el actual.")
        if not metrics["passes_all"]:
            print(f"  El modelo activo en producción ya NO pasa los criterios contra")
            print(f"  el dataset reciente. Esta es la conclusión más relevante para")
            print(f"  el Capítulo IV (resultados) y V (limitaciones) de la tesis.")
    else:
        print(f"  El modelo {args.version} se comporta de forma similar a sus métricas")
        print(f"  publicadas. No hay evidencia clara de drift.")


if __name__ == "__main__":
    main()
