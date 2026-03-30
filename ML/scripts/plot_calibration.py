"""
Visualización de calibración y diagnóstico — Ensemble v1.6.0

Genera 4 gráficas:
  1. Reliability diagram del ensemble
  2. Reliability diagram comparativo (RF solo vs Ensemble)
  3. Histograma de confianza
  4. Matriz de confusión

Uso:
    cd ML
    python -m scripts.plot_calibration
"""

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


def plot_confidence_histogram(y_proba, output_path):
    """Histograma de distribución de probabilidades predichas."""
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.hist(y_proba, bins=30, color="#2563EB", alpha=0.7, edgecolor="white")
    ax.axvline(x=0.5, color="red", linestyle="--", alpha=0.5, label="Umbral 0.5")
    ax.axvline(x=y_proba.mean(), color="green", linestyle="-", alpha=0.7,
               label=f"Media ({y_proba.mean():.3f})")

    ax.set_xlabel("P(home_win)", fontsize=12)
    ax.set_ylabel("Frecuencia", fontsize=12)
    ax.set_title("Distribución de confianza — Ensemble v1.6.0", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def plot_confusion_matrix(y_true, y_proba, output_path, threshold=0.5):
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
        title=f"Matriz de confusión — Ensemble v1.6.0 (umbral={threshold})",
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
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Cargar datos y modelo
    # ------------------------------------------------------------------
    df = load_ml_ready_games()
    X, y, feature_cols, df_clean = build_feature_matrix(df)
    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)

    X_train = df_train[feature_cols].values
    y_train = df_train[TARGET].astype(int).values
    X_test = df_test[feature_cols].values
    y_test = df_test[TARGET].astype(int).values

    # Ensemble v1.6.0
    model_path = Path(__file__).parent.parent / "models" / "nba_prediction_model_v1.6.0.joblib"
    if not model_path.exists():
        print(f"ERROR: No se encontró {model_path}")
        sys.exit(1)
    ensemble = joblib.load(model_path)
    y_proba_ens = ensemble.predict_home_win_proba(X_test)
    ece_ens = compute_ece(y_test, y_proba_ens)

    # RF solo (entrenar para comparación)
    print("\nEntrenando RF solo para comparación de calibración...")
    rf = NBARandomForest()
    rf.fit(X_train, y_train, feature_names=feature_cols)
    y_proba_rf = rf.predict_home_win_proba(X_test)
    ece_rf = compute_ece(y_test, y_proba_rf)

    print(f"\n  ECE Ensemble: {ece_ens:.4f}")
    print(f"  ECE RF solo:  {ece_rf:.4f}")

    # ------------------------------------------------------------------
    # 2. Generar gráficas
    # ------------------------------------------------------------------
    print("\nGenerando gráficas...")

    plot_reliability_diagram(
        y_test, y_proba_ens, ece_ens,
        "Curva de calibración — Ensemble v1.6.0",
        FIGURES_DIR / "calibration_v160.png",
    )

    plot_calibration_comparison(
        y_test, y_proba_rf, y_proba_ens, ece_rf, ece_ens,
        FIGURES_DIR / "calibration_comparison.png",
    )

    plot_confidence_histogram(
        y_proba_ens,
        FIGURES_DIR / "confidence_histogram.png",
    )

    plot_confusion_matrix(
        y_test, y_proba_ens,
        FIGURES_DIR / "confusion_matrix.png",
    )

    print(f"\n  Todas las gráficas guardadas en: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
