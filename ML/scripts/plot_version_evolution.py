"""
Visualización de la evolución del modelo a lo largo del versionado.

Lee todos los metadatos en `models/metadata/*_metadata.json` y genera figuras
que muestran cómo cambian las métricas entre versiones, qué criterios pasan,
y cuáles son los hitos clave (v1.6.0 baseline activo, v2.1.0 con Bivariate
Poisson). Útil para defender en la tesis la trayectoria del modelo y los
trade-offs encontrados.

NO requiere acceso a Neon — solo lee los JSON de metadatos.

Uso:
    cd ML
    python -m scripts.plot_version_evolution
    python -m scripts.plot_version_evolution --output-dir reports/figures/v2.1.0

Genera:
  - version_evolution_metrics.png      Evolución 4 métricas × N versiones
  - version_evolution_criteria.png     Heatmap pasa/falla criterios por versión
  - version_evolution_feature_count.png  Tamaño feature set vs Log Loss
  - version_summary_table.png          Tabla resumen para la tesis
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ML_ROOT = Path(__file__).parent.parent
METADATA_DIR = ML_ROOT / "models" / "metadata"
DEFAULT_FIG_DIR = ML_ROOT / "reports" / "figures"

# Criterios de aceptación oficiales del model spec
CRITERIA = {
    "log_loss":     {"op": "<", "threshold": 0.68, "label": "Log Loss",    "lower_better": True},
    "brier_score":  {"op": "<", "threshold": 0.25, "label": "Brier",       "lower_better": True},
    "roc_auc":      {"op": ">", "threshold": 0.55, "label": "ROC-AUC",     "lower_better": False},
    "ece":          {"op": "<", "threshold": 0.05, "label": "ECE",         "lower_better": True},
}

# Hitos visuales para anotar en los gráficos
HIGHLIGHTS = {
    "v1.6.0": "Baseline activo (21 features, RF+XGB)",
    "v2.0.0": "Feature set extendido (33 features)",
    "v2.1.0": "Ensemble con Bivariate Poisson (33 features)",
}

# Paleta consistente
PALETTE = {
    "passes": "#10B981",   # green
    "fails":  "#EF4444",   # red
    "neutral": "#6B7280",  # gray
    "primary": "#2563EB",  # blue
    "highlight": "#F59E0B",  # amber
}


def load_all_metadata():
    """Lee todos los metadatos disponibles ordenados semánticamente por versión."""
    files = sorted(METADATA_DIR.glob("*_metadata.json"))
    rows = []
    for path in files:
        version = path.stem.replace("_metadata", "")
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        m = meta.get("metrics", {})
        rows.append({
            "version": version,
            "model_type": meta.get("model_type", "?"),
            "n_features": len(meta.get("feature_columns", [])),
            "trained_at": meta.get("trained_at"),
            "n_test": m.get("n_samples"),
            "log_loss":    m.get("log_loss"),
            "brier_score": m.get("brier_score"),
            "roc_auc":     m.get("roc_auc"),
            "ece":         m.get("ece"),
            "accuracy":    m.get("accuracy"),
            "passes_all":  bool(m.get("passes_all", False)),
        })
    return rows


def passes(metric_key, value):
    """¿pasa la métrica el criterio del model spec?"""
    if value is None:
        return None
    spec = CRITERIA[metric_key]
    return value < spec["threshold"] if spec["op"] == "<" else value > spec["threshold"]


# --------------------------------------------------------------------------
# Figura 1 — Evolución de las 4 métricas a lo largo del versionado
# --------------------------------------------------------------------------

def plot_metrics_evolution(rows, output_path):
    """4 subplots (LogLoss, Brier, AUC, ECE) con línea de criterio y marcador
    por estado pasa/falla, con highlights en versiones clave."""
    versions = [r["version"] for r in rows]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes = axes.flatten()

    for ax, (key, spec) in zip(axes, CRITERIA.items()):
        values = [r.get(key) for r in rows]
        # Color por estado
        colors = []
        for v in values:
            ok = passes(key, v)
            colors.append(PALETTE["passes"] if ok else
                          PALETTE["fails"] if ok is False else
                          PALETTE["neutral"])

        # Línea con marcadores
        ax.plot(versions, values, "-", color=PALETTE["primary"],
                linewidth=1.5, alpha=0.5, zorder=1)
        ax.scatter(versions, values, c=colors, s=80, zorder=3, edgecolor="white", linewidth=1)

        # Línea del criterio
        ax.axhline(y=spec["threshold"], color="black", linestyle="--",
                   linewidth=1, alpha=0.6,
                   label=f"Criterio: {spec['op']} {spec['threshold']}")

        # Resaltar versiones clave
        for vname, descr in HIGHLIGHTS.items():
            if vname in versions:
                idx = versions.index(vname)
                if values[idx] is not None:
                    ax.annotate(vname, xy=(idx, values[idx]),
                                xytext=(0, 12), textcoords="offset points",
                                ha="center", fontsize=8,
                                fontweight="bold", color="black",
                                bbox=dict(boxstyle="round,pad=0.3",
                                          fc="white", ec=PALETTE["highlight"],
                                          alpha=0.9))

        ax.set_title(f"{spec['label']}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Versión", fontsize=10)
        ax.set_ylabel(spec["label"], fontsize=10)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        ax.tick_params(axis="y", labelsize=9)
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best", fontsize=9)

    fig.suptitle("Evolución de métricas predictivas a lo largo del versionado",
                 fontsize=14, fontweight="bold", y=1.00)

    # Leyenda global
    legend_handles = [
        Patch(facecolor=PALETTE["passes"], edgecolor="white", label="Pasa criterio"),
        Patch(facecolor=PALETTE["fails"], edgecolor="white", label="Falla criterio"),
        Patch(facecolor=PALETTE["neutral"], edgecolor="white", label="Sin dato"),
    ]
    fig.legend(handles=legend_handles, loc="lower center", ncol=3,
               fontsize=10, bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


# --------------------------------------------------------------------------
# Figura 2 — Heatmap pasa/falla criterios por versión
# --------------------------------------------------------------------------

def plot_criteria_heatmap(rows, output_path):
    """Matriz de pasa/falla — filas: criterios, columnas: versiones."""
    versions = [r["version"] for r in rows]
    metric_keys = list(CRITERIA.keys())
    metric_labels = [CRITERIA[k]["label"] for k in metric_keys]

    matrix = np.zeros((len(metric_keys), len(versions)))
    for j, r in enumerate(rows):
        for i, k in enumerate(metric_keys):
            v = r.get(k)
            ok = passes(k, v)
            matrix[i, j] = 1 if ok else (-1 if ok is False else 0)

    fig, ax = plt.subplots(figsize=(max(8, len(versions) * 0.7), 4))
    cmap = matplotlib.colors.ListedColormap([
        PALETTE["fails"], PALETTE["neutral"], PALETTE["passes"]
    ])
    bounds = [-1.5, -0.5, 0.5, 1.5]
    norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
    im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")

    # Anotar valor de la métrica en cada celda
    for j, r in enumerate(rows):
        for i, k in enumerate(metric_keys):
            v = r.get(k)
            if v is None:
                continue
            ok = matrix[i, j] == 1
            ax.text(j, i, f"{v:.3f}", ha="center", va="center",
                    fontsize=8, color="white" if ok else "white",
                    fontweight="bold")

    ax.set_xticks(range(len(versions)))
    ax.set_xticklabels(versions, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(metric_keys)))
    ax.set_yticklabels(metric_labels, fontsize=10)
    ax.set_title("Cumplimiento de criterios de aceptación por versión",
                 fontsize=13, fontweight="bold", pad=12)

    cbar = fig.colorbar(im, ticks=[-1, 0, 1], shrink=0.6, pad=0.02)
    cbar.set_ticklabels(["Falla", "Sin dato", "Pasa"])

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


# --------------------------------------------------------------------------
# Figura 3 — Feature count vs Log Loss
# --------------------------------------------------------------------------

def plot_feature_count_vs_quality(rows, output_path):
    """Scatter: # features (eje X) vs Log Loss (eje Y) coloreado por
    estado pasa/falla. Muestra el efecto de añadir features."""
    feats = [r["n_features"] for r in rows]
    lls = [r.get("log_loss") for r in rows]
    versions = [r["version"] for r in rows]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Trayectoria temporal con flechas
    for i in range(len(rows) - 1):
        if lls[i] is not None and lls[i+1] is not None:
            ax.annotate("",
                        xy=(feats[i+1], lls[i+1]),
                        xytext=(feats[i], lls[i]),
                        arrowprops=dict(arrowstyle="->", color="gray",
                                        alpha=0.4, lw=1))

    # Puntos
    for r, f, ll in zip(rows, feats, lls):
        if ll is None:
            continue
        ok = passes("log_loss", ll)
        color = PALETTE["passes"] if ok else PALETTE["fails"]
        ax.scatter(f, ll, c=color, s=110, edgecolor="black", linewidth=1, zorder=3)
        ax.annotate(r["version"], xy=(f, ll), xytext=(6, 6),
                    textcoords="offset points", fontsize=8)

    # Línea criterio
    ax.axhline(y=CRITERIA["log_loss"]["threshold"], color="black",
               linestyle="--", linewidth=1, alpha=0.6,
               label=f"Criterio Log Loss < {CRITERIA['log_loss']['threshold']}")

    ax.set_xlabel("Número de features", fontsize=11)
    ax.set_ylabel("Log Loss (test)", fontsize=11)
    ax.set_title("Relación entre tamaño del feature set y calidad predictiva",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


# --------------------------------------------------------------------------
# Figura 4 — Tabla resumen tipo "snapshot" para la tesis
# --------------------------------------------------------------------------

def plot_summary_table(rows, output_path):
    """Tabla con todas las versiones, sus métricas y estado, lista para
    insertar como figura en la tesis."""
    versions = [r["version"] for r in rows]
    cell_text = []
    cell_colors = []

    for r in rows:
        row_data = [
            r["version"],
            r.get("model_type", "?")[:24],
            str(r.get("n_features", "")),
            f"{r['log_loss']:.4f}"   if r.get("log_loss")    is not None else "-",
            f"{r['brier_score']:.4f}" if r.get("brier_score") is not None else "-",
            f"{r['roc_auc']:.4f}"     if r.get("roc_auc")     is not None else "-",
            f"{r['ece']:.4f}"         if r.get("ece")         is not None else "-",
            "✓" if r.get("passes_all") else "✗",
        ]
        cell_text.append(row_data)

        # Color por celda según pasa/falla
        row_colors = ["white"] * 3
        for k in ["log_loss", "brier_score", "roc_auc", "ece"]:
            v = r.get(k)
            ok = passes(k, v)
            row_colors.append("#dcfce7" if ok else
                              "#fee2e2" if ok is False else "white")
        row_colors.append("#dcfce7" if r.get("passes_all") else "#fee2e2")
        cell_colors.append(row_colors)

    headers = ["Versión", "Tipo", "#feat", "Log Loss", "Brier",
               "ROC-AUC", "ECE", "Pasa todo"]

    fig, ax = plt.subplots(figsize=(12, max(3, 0.4 * len(rows) + 1.5)))
    ax.axis("off")
    table = ax.table(cellText=cell_text, colLabels=headers,
                     cellColours=cell_colors,
                     loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.3)

    # Colorear encabezado
    for j in range(len(headers)):
        table[(0, j)].set_facecolor(PALETTE["primary"])
        table[(0, j)].set_text_props(color="white", fontweight="bold")

    title = (f"Resumen comparativo de versiones del modelo  ·  "
             f"{len(rows)} versiones registradas")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


# --------------------------------------------------------------------------
# Figura 5 — v1.6.0 publicado vs evaluado actual (data drift)
# --------------------------------------------------------------------------

def plot_data_drift_comparison(rows, output_path):
    """Compara v1.6.0 publicado en metadata vs valores que dio en evaluación
    contra el split actual (datos del usuario en evaluate_active_model)."""
    # Métricas publicadas vs reales (hardcoded — vienen del evaluate_active_model)
    drift_data = {
        "v1.6.0": {
            "publicado":  {"log_loss": 0.6553, "brier_score": 0.2312, "roc_auc": 0.6542, "ece": 0.0363},
            "actual":     {"log_loss": 0.6926, "brier_score": 0.2477, "roc_auc": 0.6194, "ece": 0.0844},
        },
        "v2.1.0": {
            "publicado":  {"log_loss": 0.6857, "brier_score": 0.2420, "roc_auc": 0.6511, "ece": 0.0839},
            "actual":     {"log_loss": 0.6857, "brier_score": 0.2420, "roc_auc": 0.6511, "ece": 0.0839},
        },
    }

    metric_keys = list(CRITERIA.keys())
    fig, axes = plt.subplots(1, 4, figsize=(16, 5))

    width = 0.35
    x = np.arange(len(drift_data))
    versions_x = list(drift_data.keys())

    for ax, key in zip(axes, metric_keys):
        spec = CRITERIA[key]
        publicado = [drift_data[v]["publicado"][key] for v in versions_x]
        actual    = [drift_data[v]["actual"][key]    for v in versions_x]

        bars1 = ax.bar(x - width/2, publicado, width,
                       label="Publicado", color=PALETTE["primary"], alpha=0.85)
        bars2 = ax.bar(x + width/2, actual,    width,
                       label="Evaluación split actual", color=PALETTE["highlight"], alpha=0.85)

        ax.axhline(y=spec["threshold"], color="black", linestyle="--",
                   linewidth=1, alpha=0.5, label=f"Criterio {spec['op']} {spec['threshold']}")

        for bar, val in zip(bars1, publicado):
            ax.annotate(f"{val:.3f}",
                        xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8)
        for bar, val in zip(bars2, actual):
            ax.annotate(f"{val:.3f}",
                        xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(versions_x)
        ax.set_title(spec["label"], fontsize=11, fontweight="bold")
        ax.set_ylabel(spec["label"], fontsize=10)
        ax.legend(fontsize=8, loc="best")
        ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle("Data drift estacional: métricas publicadas vs evaluación contra split 2025-12 → 2026-03",
                 fontsize=13, fontweight="bold", y=1.02)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", default=str(DEFAULT_FIG_DIR),
                        help="Directorio de salida (default: reports/figures)")
    parser.add_argument("--skip-drift", action="store_true",
                        help="No generar la figura de data drift")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nLeyendo metadatos de {METADATA_DIR}...")
    rows = load_all_metadata()
    if not rows:
        print("No hay metadatos. Ejecutar primero entrenamientos.")
        sys.exit(1)
    print(f"  {len(rows)} versiones cargadas: {[r['version'] for r in rows]}")

    print(f"\nGenerando figuras en {output_dir}...")
    plot_metrics_evolution(rows, output_dir / "version_evolution_metrics.png")
    plot_criteria_heatmap(rows, output_dir / "version_evolution_criteria.png")
    plot_feature_count_vs_quality(rows, output_dir / "version_evolution_feature_count.png")
    plot_summary_table(rows, output_dir / "version_summary_table.png")
    if not args.skip_drift:
        plot_data_drift_comparison(rows, output_dir / "data_drift_v160_vs_actual.png")

    print(f"\n[OK] {5 if not args.skip_drift else 4} figuras generadas en {output_dir}")


if __name__ == "__main__":
    main()
