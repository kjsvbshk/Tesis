"""
Visualización de la calidad de los regresores team-props (v2.2.0).

Para cada stat (rebotes, asistencias, robos, bloqueos, turnovers) y cada
equipo (home / away), genera:
  - scatter de predicciones vs reales con línea ideal (y=x)
  - distribución de errores
  - tabla resumen de MAE / RMSE / bias / correlación

Uso:
    cd ML
    python -m scripts.plot_props_calibration                       # versión por defecto v2.2.0
    python -m scripts.plot_props_calibration --version v2.2.0
    python -m scripts.plot_props_calibration --version v2.2.0 --output-dir reports/figures/v2.2.0
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

ML_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ML_ROOT))

from src.training.train import (
    load_ml_ready_games,
    build_feature_matrix,
    DATE_COL,
)
from src.evaluation.validation import temporal_train_test_split
from src.models.ensemble import TEAM_STAT_KINDS, TEAM_STAT_LABELS


def regression_metrics(y_true, y_pred):
    valid = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if valid.sum() == 0:
        return {"mae": None, "rmse": None, "bias": None, "corr": None, "n": 0}
    yt, yp = y_true[valid], y_pred[valid]
    return {
        "mae":  float(np.mean(np.abs(yt - yp))),
        "rmse": float(np.sqrt(np.mean((yt - yp) ** 2))),
        "bias": float(np.mean(yp - yt)),
        "corr": float(np.corrcoef(yt, yp)[0, 1]) if len(yt) > 1 else 0.0,
        "n":    int(valid.sum()),
    }


def plot_props_grid(team_props_pred, df_test, output_path, version):
    """Grid 5×2 — scatter pred vs real para cada stat × side."""
    fig, axes = plt.subplots(5, 2, figsize=(11, 18))
    metrics_table = []

    for i, kind in enumerate(TEAM_STAT_KINDS):
        for j, side in enumerate(("home", "away")):
            ax = axes[i, j]
            col = f"{side}_{kind}"
            if col not in df_test.columns or kind not in team_props_pred[side]:
                ax.text(0.5, 0.5, f"Sin datos ({col})",
                        ha="center", va="center", transform=ax.transAxes)
                ax.set_axis_off()
                continue
            y_true = df_test[col].astype(float).values
            y_pred = team_props_pred[side][kind]

            m = regression_metrics(y_true, y_pred)
            metrics_table.append({"stat": kind, "side": side, **m})

            valid = ~np.isnan(y_true) & ~np.isnan(y_pred)
            ax.scatter(y_true[valid], y_pred[valid], alpha=0.3, s=10,
                       color="#2563EB" if side == "home" else "#F59E0B")

            # Línea ideal y = x
            mn = min(y_true[valid].min(), y_pred[valid].min())
            mx = max(y_true[valid].max(), y_pred[valid].max())
            ax.plot([mn, mx], [mn, mx], "k--", alpha=0.4, label="y = x")

            # Línea de regresión
            if valid.sum() > 1:
                slope, intercept = np.polyfit(y_true[valid], y_pred[valid], 1)
                xs = np.linspace(mn, mx, 50)
                ax.plot(xs, slope * xs + intercept, "-", color="red",
                        linewidth=1.3, alpha=0.6, label=f"Ajuste (r={m['corr']:.2f})")

            label = TEAM_STAT_LABELS.get(kind, kind)
            ax.set_title(f"{label} — {side.upper()}  "
                         f"MAE={m['mae']:.2f}  bias={m['bias']:+.2f}",
                         fontsize=10)
            ax.set_xlabel("Real")
            ax.set_ylabel("Predicho")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8, loc="best")

    fig.suptitle(f"Calibración team-props · {version}",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")
    return metrics_table


def plot_props_summary_table(metrics_table, output_path, version):
    """Tabla resumen MAE / RMSE / bias / corr por stat × side."""
    headers = ["Stat", "Equipo", "MAE", "RMSE", "Bias", "Corr", "N"]
    rows = []
    for m in metrics_table:
        label = TEAM_STAT_LABELS.get(m["stat"], m["stat"])
        rows.append([
            label,
            m["side"].upper(),
            f"{m['mae']:.3f}"  if m["mae"]  is not None else "-",
            f"{m['rmse']:.3f}" if m["rmse"] is not None else "-",
            f"{m['bias']:+.3f}" if m["bias"] is not None else "-",
            f"{m['corr']:.3f}" if m["corr"] is not None else "-",
            f"{m['n']}",
        ])

    fig, ax = plt.subplots(figsize=(11, max(3, 0.4 * len(rows) + 1.5)))
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=headers,
                     loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.4)
    for j in range(len(headers)):
        table[(0, j)].set_facecolor("#2563EB")
        table[(0, j)].set_text_props(color="white", fontweight="bold")

    ax.set_title(f"Resumen team-props · {version}",
                 fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def plot_error_distribution(team_props_pred, df_test, output_path, version):
    """Histograma de errores (residual = pred − real) por stat."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.flatten()

    for ax, kind in zip(axes, TEAM_STAT_KINDS):
        all_errors = []
        for side in ("home", "away"):
            col = f"{side}_{kind}"
            if col not in df_test.columns or kind not in team_props_pred[side]:
                continue
            y_true = df_test[col].astype(float).values
            y_pred = team_props_pred[side][kind]
            valid = ~np.isnan(y_true) & ~np.isnan(y_pred)
            errors = y_pred[valid] - y_true[valid]
            ax.hist(errors, bins=30, alpha=0.5,
                    label=side.upper(),
                    color="#2563EB" if side == "home" else "#F59E0B")
            all_errors.extend(errors.tolist())

        ax.axvline(x=0, color="black", linestyle="--", alpha=0.5)
        ax.set_title(f"{TEAM_STAT_LABELS.get(kind, kind)}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Error (Predicho − Real)")
        ax.set_ylabel("Frecuencia")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    # Apaga subplots vacíos
    for k in range(len(TEAM_STAT_KINDS), len(axes)):
        axes[k].set_axis_off()

    fig.suptitle(f"Distribución de errores team-props · {version}",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
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

    output_dir = Path(args.output_dir) if args.output_dir else (ML_ROOT / "reports" / "figures")
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = ML_ROOT / "models" / f"nba_prediction_model_{args.version}.joblib"
    if not model_path.exists():
        print(f"❌ No existe: {model_path}")
        print("   Entrena primero: python -m src.training.train --version "
              f"{args.version} --model ensemble")
        sys.exit(1)

    print(f"\nCargando modelo: {model_path}")
    model = joblib.load(model_path)
    if not getattr(model, "team_stat_models", None):
        print(f"❌ El modelo {args.version} no tiene team_stat_models. "
              "Re-entrena con v2.2.0 para incluirlos.")
        sys.exit(1)

    print(f"  Modelos team-props cargados: {sorted(model.team_stat_models.keys())}")

    # Cargar split temporal idéntico al de entrenamiento
    df = load_ml_ready_games()
    X, y, feature_cols, df_clean = build_feature_matrix(df)
    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)
    X_test = df_test[feature_cols].values

    print(f"\n  Test set: n={len(X_test)} ({df_test[DATE_COL].min()} → {df_test[DATE_COL].max()})")

    full = model.predict_full(X_test)
    if "team_props" not in full:
        print("❌ predict_full no expone team_props.")
        sys.exit(1)
    team_props_pred = full["team_props"]

    # Generar figuras
    print(f"\nGenerando figuras en {output_dir}...")
    metrics = plot_props_grid(team_props_pred, df_test,
                              output_dir / f"props_calibration_grid_{args.version}.png",
                              args.version)
    plot_props_summary_table(metrics,
                             output_dir / f"props_summary_table_{args.version}.png",
                             args.version)
    plot_error_distribution(team_props_pred, df_test,
                            output_dir / f"props_error_distribution_{args.version}.png",
                            args.version)

    # Guardar JSON con métricas para el reporte
    import json
    json_path = output_dir.parent / f"props_metrics_{args.version}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  Métricas JSON: {json_path}")


if __name__ == "__main__":
    main()
