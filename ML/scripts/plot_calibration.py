"""
Visualización de calibración y diagnóstico — Ensemble (cualquier versión).

Genera 4 gráficas:
  1. Reliability diagram del ensemble
  2. Reliability diagram comparativo (RF solo vs Ensemble)
  3. Histograma de confianza
  4. Matriz de confusión

Uso:
    cd ML
    python -m scripts.plot_calibration                       # v2.2.0 (default)
    python -m scripts.plot_calibration --version v2.1.0
    python -m scripts.plot_calibration --version v1.6.0 --output-dir reports/figures/v1.6.0
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.train import (
    load_ml_ready_games,
    build_feature_matrix,
    TARGET,
    DATE_COL,
)
from src.evaluation.validation import temporal_train_test_split
from src.evaluation.metrics import compute_ece
from src.models.random_forest import NBARandomForest

FIGURES_DIR = Path(__file__).parent.parent / "reports" / "figures"


def calibration_data(y_true, y_proba, n_bins=10):
    """Calcula datos de calibración por bin."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = []
    bin_accuracies = []
    bin_counts = []

    for i in range(n_bins):
        mask = (y_proba >= bins[i]) & (y_proba < bins[i + 1])
        count = mask.sum()
        if count == 0:
            continue
        bin_centers.append(y_proba[mask].mean())
        bin_accuracies.append(y_true[mask].mean())
        bin_counts.append(count)

    return np.array(bin_centers), np.array(bin_accuracies), np.array(bin_counts)


def plot_reliability_diagram(y_true, y_proba, ece, title, output_path):
    """Reliability diagram con barras de frecuencia."""
    centers, accuracies, counts = calibration_data(y_true, y_proba)

    fig, ax1 = plt.subplots(figsize=(8, 6))

    # Línea de calibración perfecta
    ax1.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Calibración perfecta")

    # Puntos de calibración
    ax1.plot(centers, accuracies, "o-", color="#2563EB", linewidth=2,
             markersize=8, label=f"Modelo (ECE={ece:.4f})")

    # Rellenar gap
    for c, a in zip(centers, accuracies):
        color = "#EF4444" if abs(a - c) > 0.05 else "#10B981"
        ax1.plot([c, c], [c, a], color=color, linewidth=1.5, alpha=0.6)

    ax1.set_xlabel("Probabilidad predicha", fontsize=12)
    ax1.set_ylabel("Frecuencia observada", fontsize=12)
    ax1.set_title(title, fontsize=14)
    ax1.set_xlim(-0.02, 1.02)
    ax1.set_ylim(-0.02, 1.02)
    ax1.legend(loc="upper left", fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Barras de frecuencia (eje secundario)
    ax2 = ax1.twinx()
    bar_width = 0.08
    ax2.bar(centers, counts, width=bar_width, alpha=0.2, color="gray", label="N muestras")
    ax2.set_ylabel("N muestras por bin", fontsize=10, color="gray")
    ax2.tick_params(axis="y", labelcolor="gray")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def plot_calibration_comparison(y_true, proba_rf, proba_ens, ece_rf, ece_ens, output_path):
    """Reliability diagram comparativo RF vs Ensemble."""
    centers_rf, acc_rf, _ = calibration_data(y_true, proba_rf)
    centers_ens, acc_ens, _ = calibration_data(y_true, proba_ens)

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Calibración perfecta")
    ax.plot(centers_rf, acc_rf, "s-", color="#F59E0B", linewidth=2,
            markersize=7, label=f"RF solo (ECE={ece_rf:.4f})")
    ax.plot(centers_ens, acc_ens, "o-", color="#2563EB", linewidth=2,
            markersize=7, label=f"Ensemble (ECE={ece_ens:.4f})")

    ax.set_xlabel("Probabilidad predicha", fontsize=12)
    ax.set_ylabel("Frecuencia observada", fontsize=12)
    ax.set_title("Calibración: Random Forest vs Ensemble", fontsize=14)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def plot_confidence_histogram(y_proba, output_path, version="v?"):
    """Histograma de distribución de probabilidades predichas."""
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.hist(y_proba, bins=30, color="#2563EB", alpha=0.7, edgecolor="white")
    ax.axvline(x=0.5, color="red", linestyle="--", alpha=0.5, label="Umbral 0.5")
    ax.axvline(x=y_proba.mean(), color="green", linestyle="-", alpha=0.7,
               label=f"Media ({y_proba.mean():.3f})")

    ax.set_xlabel("P(home_win)", fontsize=12)
    ax.set_ylabel("Frecuencia", fontsize=12)
    ax.set_title(f"Distribución de confianza — Ensemble {version}", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def plot_confusion_matrix(y_true, y_proba, output_path, threshold=0.5, version="v?"):
    """Matriz de confusión."""
    y_pred = (y_proba >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)

    fig, ax = plt.subplots(figsize=(6, 5))

    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    fig.colorbar(im, ax=ax)

    labels = ["Away win (0)", "Home win (1)"]
    ax.set(
        xticks=[0, 1], yticks=[0, 1],
        xticklabels=labels, yticklabels=labels,
        xlabel="Predicho", ylabel="Real",
        title=f"Matriz de confusión — Ensemble {version} (umbral={threshold})",
    )

    # Anotar valores
    for i in range(2):
        for j in range(2):
            color = "white" if cm[i, j] > cm.max() / 2 else "black"
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color=color, fontsize=18, fontweight="bold")

    # Métricas
    total = cm.sum()
    accuracy = (cm[0, 0] + cm[1, 1]) / total
    ax.text(0.5, -0.15, f"Accuracy: {accuracy:.2%}  (n={total})",
            ha="center", va="top", transform=ax.transAxes, fontsize=11)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default="v2.2.0",
                        help="Versión del modelo (default: v2.2.0)")
    parser.add_argument("--output-dir", default=None,
                        help="Directorio de salida (default: reports/figures)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else FIGURES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Cargar modelo PRIMERO para inferir el feature set correcto
    # ------------------------------------------------------------------
    model_path = Path(__file__).parent.parent / "models" / f"nba_prediction_model_{args.version}.joblib"
    if not model_path.exists():
        print(f"ERROR: No se encontró {model_path}")
        print(f"Entrena primero: python -m src.training.train --version {args.version} --model ensemble")
        sys.exit(1)
    print(f"\nCargando modelo: {model_path}")
    ensemble = joblib.load(model_path)

    # Inferir el feature set que espera el modelo (21 para v1.x, 33 para v2.x)
    # y filtrar X_test/X_train acorde — el modelo v1.6.0 fue entrenado con 21
    # features y falla si recibe 33; el v2.x con 33 y falla si recibe 21.
    from scripts.evaluate_active_model import predict_legacy, detect_feature_set
    from tests.ablation_study import FEATURE_SETS
    try:
        feature_set = detect_feature_set(ensemble)
    except Exception:
        feature_set = "v2"
    requested = FEATURE_SETS[feature_set]
    print(f"  Feature set inferido: {feature_set} ({len(requested)} features)")

    # ------------------------------------------------------------------
    # 2. Cargar datos con el feature set correcto
    # ------------------------------------------------------------------
    df = load_ml_ready_games()
    X, y, all_feature_cols, df_clean = build_feature_matrix(df)
    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)

    feature_cols = [c for c in requested if c in df_clean.columns]
    if len(feature_cols) != len(requested):
        missing = [c for c in requested if c not in df_clean.columns]
        print(f"  Aviso: features ausentes en BD ({len(missing)}): {missing}")

    X_train = df_train[feature_cols].values
    y_train = df_train[TARGET].astype(int).values
    X_test = df_test[feature_cols].values
    y_test = df_test[TARGET].astype(int).values

    # predict_legacy maneja todas las versiones (v1.x: 2D, v2.1.0: 3D, v2.1.2/v2.2.0: 4D)
    try:
        y_proba_ens = predict_legacy(ensemble, X_test)
    except Exception as e:
        print(f"  Advertencia: predict_legacy falló ({e}); usando predict_home_win_proba directo")
        y_proba_ens = ensemble.predict_home_win_proba(X_test)
    ece_ens = compute_ece(y_test, y_proba_ens)

    # RF solo (entrenar para comparación) — usa el MISMO feature set que el modelo
    print("\nEntrenando RF solo para comparación de calibración...")
    rf = NBARandomForest()
    rf.fit(X_train, y_train, feature_names=feature_cols)
    y_proba_rf = rf.predict_home_win_proba(X_test)
    ece_rf = compute_ece(y_test, y_proba_rf)

    print(f"\n  ECE Ensemble {args.version}: {ece_ens:.4f}")
    print(f"  ECE RF solo:               {ece_rf:.4f}")

    # ------------------------------------------------------------------
    # 2. Generar gráficas
    # ------------------------------------------------------------------
    print(f"\nGenerando gráficas en {out_dir}...")

    plot_reliability_diagram(
        y_test, y_proba_ens, ece_ens,
        f"Curva de calibración — Ensemble {args.version}",
        out_dir / f"calibration_{args.version}.png",
    )

    plot_calibration_comparison(
        y_test, y_proba_rf, y_proba_ens, ece_rf, ece_ens,
        out_dir / f"calibration_comparison_{args.version}.png",
    )

    plot_confidence_histogram(
        y_proba_ens,
        out_dir / f"confidence_histogram_{args.version}.png",
        version=args.version,
    )

    plot_confusion_matrix(
        y_test, y_proba_ens,
        out_dir / f"confusion_matrix_{args.version}.png",
        version=args.version,
    )

    print(f"\n  Todas las gráficas guardadas en: {out_dir}")


if __name__ == "__main__":
    main()
