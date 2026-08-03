"""
Calibración e histograma de confianza del MODELO ACTIVO (v3.1.0) para la
sustentación — con la paleta exclusiva de la presentación.

A diferencia de plot_pres_versions.py, este script SÍ necesita:
  - Conexión a Neon (lee ml.ml_ready_games mediante src/training/train.py)
  - El archivo models/nba_prediction_model_v3.1.0.joblib

Reproduce el split temporal 80/20, carga el modelo, predice sobre el conjunto
de prueba y grafica la curva de fiabilidad y la distribución de probabilidades.

Paleta EXCLUSIVA:
    #B30016 rojo · #151A52 azul marino · #30308F azul índigo · #808080 gris · #FFFFFF blanco

Uso:
    cd ML
    python -m scripts.plot_pres_calibration
    python -m scripts.plot_pres_calibration --version v3.1.0 --output-dir reports/figures/pres

Genera:
    pres_calibration_v3.1.0.png            Curva de fiabilidad (reliability diagram)
    pres_confidence_histogram_v3.1.0.png   Distribución de P(home_win)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.train import load_ml_ready_games, build_feature_matrix, TARGET, DATE_COL
from src.evaluation.validation import temporal_train_test_split
from src.evaluation.metrics import compute_ece

# ── Paleta exclusiva ────────────────────────────────────────────────────────
RED, NAVY, INDIGO, GRAY, WHITE = "#B30016", "#151A52", "#30308F", "#808080", "#FFFFFF"
plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"],
    "axes.edgecolor": NAVY, "axes.labelcolor": NAVY, "text.color": NAVY,
    "xtick.color": NAVY, "ytick.color": NAVY, "axes.titlecolor": NAVY,
})

ML_ROOT = Path(__file__).parent.parent
FIG_DIR = ML_ROOT / "reports" / "figures"


def reliability_bins(y_true, y_proba, n_bins=10):
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    centers, acc, counts = [], [], []
    for i in range(n_bins):
        m = (y_proba >= edges[i]) & (y_proba < edges[i + 1] if i < n_bins - 1 else y_proba <= edges[i + 1])
        if m.sum() == 0:
            continue
        centers.append(y_proba[m].mean())
        acc.append(y_true[m].mean())
        counts.append(int(m.sum()))
    return np.array(centers), np.array(acc), np.array(counts)


def plot_reliability(y_true, y_proba, ece, version, out_path):
    centers, acc, counts = reliability_bins(y_true, y_proba)
    fig, ax = plt.subplots(figsize=(7.2, 5.4))

    # Barras de conteo por bin (eje secundario), en gris tenue
    ax2 = ax.twinx()
    ax2.bar(centers, counts, width=0.08, color=GRAY, alpha=0.25, zorder=1)
    ax2.set_ylabel("N.º de muestras por bin", fontsize=10, color=GRAY)
    ax2.tick_params(axis="y", labelcolor=GRAY)

    # Diagonal de calibración perfecta
    ax.plot([0, 1], [0, 1], "--", color=GRAY, linewidth=1.4, label="Calibración perfecta", zorder=2)
    # Curva del modelo
    ax.plot(centers, acc, "o-", color=INDIGO, linewidth=2.2, markersize=8,
            markeredgecolor=WHITE, markeredgewidth=1.2,
            label=f"Modelo {version} (ECE = {ece:.4f})", zorder=4)
    # Desviaciones respecto a la diagonal
    for c, a in zip(centers, acc):
        ax.plot([c, c], [c, a], color=RED, linewidth=1.3, alpha=0.7, zorder=3)

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("Probabilidad predicha", fontsize=12)
    ax.set_ylabel("Frecuencia observada", fontsize=12)
    ax.set_title(f"CURVA DE CALIBRACIÓN — ENSEMBLE {version.upper()}", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.2, color=GRAY)
    ax.legend(loc="upper left", fontsize=10)
    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


def plot_confidence_histogram(y_proba, version, out_path):
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.hist(y_proba, bins=30, color=INDIGO, alpha=0.85, edgecolor=WHITE)
    ax.axvline(0.5, color=RED, linestyle="--", linewidth=1.5, label="Umbral 0,5")
    ax.axvline(float(np.mean(y_proba)), color=NAVY, linewidth=1.8,
               label=f"Media ({np.mean(y_proba):.3f})")
    ax.set_xlabel("P(home_win)", fontsize=12)
    ax.set_ylabel("Frecuencia", fontsize=12)
    ax.set_title(f"DISTRIBUCIÓN DE CONFIANZA — ENSEMBLE {version.upper()}", fontsize=13, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.2, color=GRAY)
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


def main():
    ap = argparse.ArgumentParser(description="Calibración del modelo activo para la sustentación")
    ap.add_argument("--version", default="v3.1.0", help="Versión del modelo (default: v3.1.0)")
    ap.add_argument("--output-dir", default=str(FIG_DIR))
    args = ap.parse_args()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)

    model_path = ML_ROOT / "models" / f"nba_prediction_model_{args.version}.joblib"
    if not model_path.exists():
        print(f"ERROR: no se encontró {model_path}")
        print(f"Entrena/exporta primero: python -m src.training.train --version {args.version}")
        sys.exit(1)

    print(f"Cargando modelo activo: {model_path}")
    ensemble = joblib.load(model_path)

    print("Cargando ml.ml_ready_games y construyendo features (52, defaults v3.1.0)...")
    df = load_ml_ready_games()
    X, y, feature_cols, df_clean = build_feature_matrix(df)  # use_odds=True, use_v3=True por defecto
    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)
    X_test = df_test[feature_cols].values
    y_test = df_test[TARGET].astype(int).values
    print(f"  Test: {len(y_test)} partidos · {len(feature_cols)} features")

    # v3.1.0 es la arquitectura actual del código → predicción directa
    try:
        y_proba = ensemble.predict_home_win_proba(X_test)
    except Exception as e:
        print(f"  predict directo falló ({e}); reconstruyendo por componentes...")
        from scripts.evaluate_active_model import predict_legacy
        y_proba = predict_legacy(ensemble, X_test)

    ece = compute_ece(y_test, y_proba)
    print(f"  ECE {args.version} sobre el split de prueba: {ece:.4f}")

    plot_reliability(y_test, y_proba, ece, args.version,
                     out / f"pres_calibration_{args.version}.png")
    plot_confidence_histogram(y_proba, args.version,
                              out / f"pres_confidence_histogram_{args.version}.png")
    print("Listo.")


if __name__ == "__main__":
    main()
