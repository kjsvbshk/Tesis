"""
Comparación de baselines contra el modelo Ensemble v2.0.0.

Demuestra que el ensemble supera enfoques simples (heurísticas)
y modelos individuales (LR, RF solo, XGB solo).

Uso:
    cd ML
    python -m scripts.baselines
"""

import sys
import json
from pathlib import Path

import numpy as np
import joblib
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.train import (
    load_ml_ready_games,
    build_feature_matrix,
    DIFF_FEATURES,
    INDIVIDUAL_FEATURES,
    TARGET,
    DATE_COL,
)
from src.evaluation.validation import temporal_train_test_split
from src.evaluation.metrics import evaluate_classifier
from src.models.random_forest import NBARandomForest


def run_baselines():
    # ------------------------------------------------------------------
    # 1. Cargar datos y construir features (misma partición que v2.0.0)
    # ------------------------------------------------------------------
    df = load_ml_ready_games()
    X, y, feature_cols, df_clean = build_feature_matrix(df)
    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)

    X_train = df_train[feature_cols].values
    y_train = df_train[TARGET].astype(int).values
    X_test = df_test[feature_cols].values
    y_test = df_test[TARGET].astype(int).values

    home_win_rate = y_train.mean()
    print(f"\nHome win rate (train): {home_win_rate:.4f}")

    results = []

    # ------------------------------------------------------------------
    # Baseline 1: Siempre local (P=1.0)
    # ------------------------------------------------------------------
    print("\n[1/7] Evaluando: Siempre local...")
    y_proba_home = np.ones(len(y_test))
    # Log loss necesita probabilidades en (0,1), no exactamente 1.0
    y_proba_home_clipped = np.full(len(y_test), 0.9999)
    metrics = evaluate_classifier(y_test, y_proba_home_clipped, label="Siempre local")
    # Override accuracy con la real (threshold 0.5 con P=0.9999 predice siempre 1)
    metrics["model"] = "Siempre local"
    results.append(metrics)

    # ------------------------------------------------------------------
    # Baseline 2: Moneda al aire (P=0.5)
    # ------------------------------------------------------------------
    print("[2/7] Evaluando: Moneda al aire...")
    y_proba_coin = np.full(len(y_test), 0.5)
    metrics = evaluate_classifier(y_test, y_proba_coin, label="Moneda al aire")
    metrics["model"] = "Moneda al aire"
    results.append(metrics)

    # ------------------------------------------------------------------
    # Baseline 3: Home win rate fijo
    # ------------------------------------------------------------------
    print("[3/7] Evaluando: Home win rate fijo...")
    y_proba_rate = np.full(len(y_test), home_win_rate)
    metrics = evaluate_classifier(y_test, y_proba_rate, label="Home win rate fijo")
    metrics["model"] = f"Home win rate fijo ({home_win_rate:.2%})"
    results.append(metrics)

    # ------------------------------------------------------------------
    # Baseline 4: Logistic Regression
    # ------------------------------------------------------------------
    print("[4/7] Entrenando: Logistic Regression...")
    lr_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(C=0.5, max_iter=1000, random_state=42)),
    ])
    lr_pipeline.fit(X_train, y_train)
    y_proba_lr = lr_pipeline.predict_proba(X_test)[:, 1]
    metrics = evaluate_classifier(y_test, y_proba_lr, label="Logistic Regression")
    metrics["model"] = "Logistic Regression"
    results.append(metrics)

    # ------------------------------------------------------------------
    # Baseline 5: Random Forest solo
    # ------------------------------------------------------------------
    print("[5/7] Entrenando: Random Forest solo...")
    rf = NBARandomForest()
    rf.fit(X_train, y_train, feature_names=feature_cols)
    y_proba_rf = rf.predict_home_win_proba(X_test)
    metrics = evaluate_classifier(y_test, y_proba_rf, label="Random Forest solo")
    metrics["model"] = "Random Forest solo"
    results.append(metrics)

    # ------------------------------------------------------------------
    # Baseline 6: XGBoost clasificador solo
    # ------------------------------------------------------------------
    print("[6/7] Entrenando: XGBoost clasificador...")
    xgb_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("xgb", XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=10,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
            eval_metric="logloss",
        )),
    ])
    xgb_pipeline.fit(X_train, y_train)
    y_proba_xgb = xgb_pipeline.predict_proba(X_test)[:, 1]
    metrics = evaluate_classifier(y_test, y_proba_xgb, label="XGBoost clasificador")
    metrics["model"] = "XGBoost clasificador"
    results.append(metrics)

    # ------------------------------------------------------------------
    # Modelo 7: Ensemble v2.0.0 (33 features)
    # ------------------------------------------------------------------
    print("[7/7] Cargando: Ensemble v2.0.0...")
    model_path = Path(__file__).parent.parent / "models" / "nba_prediction_model_v2.0.0.joblib"
    if model_path.exists():
        ensemble = joblib.load(model_path)
        y_proba_ens = ensemble.predict_home_win_proba(X_test)
        metrics = evaluate_classifier(y_test, y_proba_ens, label="Ensemble v2.0.0")
        metrics["model"] = "Ensemble v2.0.0"
        results.append(metrics)
    else:
        print(f"  ADVERTENCIA: No se encontró {model_path}")
        print("  Entrenando ensemble fresco para comparación...")
        from src.training.train import train_ensemble
        ensemble = train_ensemble(X_train, y_train, df_train, feature_cols)
        y_proba_ens = ensemble.predict_home_win_proba(X_test)
        metrics = evaluate_classifier(y_test, y_proba_ens, label="Ensemble v2.0.0")
        metrics["model"] = "Ensemble v2.0.0"
        results.append(metrics)

    # ------------------------------------------------------------------
    # Tabla comparativa
    # ------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("  COMPARACIÓN DE BASELINES")
    print("=" * 90)
    header = f"  {'Modelo':<30} {'Log Loss':>9} {'Brier':>9} {'ROC-AUC':>9} {'ECE':>9} {'Accuracy':>9}"
    print(header)
    print("  " + "-" * 86)

    for r in results:
        model_name = r["model"][:30]
        print(f"  {model_name:<30} {r['log_loss']:>9.4f} {r['brier_score']:>9.4f} "
              f"{r['roc_auc']:>9.4f} {r['ece']:>9.4f} {r['accuracy']:>9.4f}")

    print("=" * 90)

    # Encontrar mejor modelo por Log Loss (excluyendo heurísticas con AUC=0.5)
    ml_models = [r for r in results if r["roc_auc"] > 0.50]
    if ml_models:
        best = min(ml_models, key=lambda x: x["log_loss"])
        print(f"\n  Mejor modelo (menor Log Loss): {best['model']} ({best['log_loss']:.4f})")

    # ------------------------------------------------------------------
    # Guardar JSON
    # ------------------------------------------------------------------
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    output_path = reports_dir / "baselines_comparison_v3.json"

    # Limpiar para JSON (convertir numpy types)
    clean_results = []
    for r in results:
        clean = {}
        for k, v in r.items():
            if isinstance(v, (np.integer, np.int64)):
                clean[k] = int(v)
            elif isinstance(v, (np.floating, np.float64)):
                clean[k] = float(v)
            elif isinstance(v, np.bool_):
                clean[k] = bool(v)
            else:
                clean[k] = v
        clean_results.append(clean)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean_results, f, indent=2, ensure_ascii=False)

    print(f"\n  Resultados guardados: {output_path}")


if __name__ == "__main__":
    run_baselines()
