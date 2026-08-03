"""
Figuras de versionado para la SUSTENTACIÓN — actualizadas hasta v3.1.0.

Genera las figuras basadas en la trayectoria de versiones usando una tabla
CANÓNICA (los valores publicados en el documento + v3.0.0 y v3.1.0), en lugar
de leer los metadatos JSON del repositorio, que quedaron descuadrados tras los
reentrenamientos posteriores (p.ej. v1.6.0_metadata.json contiene hoy 33
features y métricas de v2.2.0).

NO requiere Neon ni el .joblib: solo matplotlib + numpy. Totalmente reproducible.

Paleta EXCLUSIVA de la presentación:
    #B30016  rojo        → falla criterio / degradación
    #151A52  azul marino → estructura / valor "publicado"
    #30308F  azul índigo → pasa criterio / modelo recuperado
    #808080  gris        → sin dato / referencia
    #FFFFFF  blanco      → fondo / bordes

Uso:
    cd ML
    python -m scripts.plot_pres_versions
    python -m scripts.plot_pres_versions --output-dir reports/figures/pres

Genera:
    pres_version_evolution_metrics.png   Evolución de 4 métricas (16 versiones)
    pres_version_criteria.png            Heatmap pasa/falla por versión y métrica
    pres_feature_vs_logloss.png          Tamaño del feature set vs Log Loss
    pres_drift_comparison.png            Drift v1.6.0 vs recuperación v3.1.0
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.colors as mcolors

# ── Paleta exclusiva ────────────────────────────────────────────────────────
RED    = "#B30016"   # falla / degradación
NAVY   = "#151A52"   # estructura / publicado
INDIGO = "#30308F"   # pasa / recuperado
GRAY   = "#808080"   # sin dato / referencia
WHITE  = "#FFFFFF"

# Fuente de marca: Arial (con respaldos por si no está instalada).
# Títulos y subtítulos van en MAYÚSCULA SOSTENIDA y negrita.
plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"],
    "axes.edgecolor": NAVY,
    "axes.labelcolor": NAVY,
    "text.color": NAVY,
    "xtick.color": NAVY,
    "ytick.color": NAVY,
    "axes.titlecolor": NAVY,
})

DEFAULT_FIG_DIR = Path(__file__).parent.parent / "reports" / "figures"

# ── Criterios de aceptación del model spec ──────────────────────────────────
CRITERIA = {
    "log_loss":    {"op": "<", "threshold": 0.68, "label": "Log Loss"},
    "brier_score": {"op": "<", "threshold": 0.25, "label": "Brier"},
    "roc_auc":     {"op": ">", "threshold": 0.55, "label": "ROC-AUC"},
    "ece":         {"op": "<", "threshold": 0.05, "label": "ECE"},
}

# ── Tabla CANÓNICA de versiones ──────────────────────────────────────────────
# Se lee desde reports/canonical_versions.json (fuente de verdad versionada).
# Motivo: models/metadata/*.json quedó parcialmente corrupto — v1.6.0 y v2.2.0
# fueron sobrescritos por reentrenamientos que reutilizaron el número de versión.
# El JSON canónico contiene los valores oficiales del documento + v3.0.0/v3.1.0.
# Si el archivo no existe, se usa la tabla de respaldo (idéntica) hardcodeada.
CANONICAL_JSON = Path(__file__).parent.parent / "reports" / "canonical_versions.json"

_FALLBACK = [
    ("v1.0.0", 18, 0.5436, 0.1588, 0.8530, 0.2226),
    ("v1.1.0", 21, 0.8857, 0.2434, 0.6799, 0.2651),
    ("v1.1.1", 21, 0.6249, 0.2110, 0.7193, 0.2322),
    ("v1.1.2", 21, 0.6205, 0.2117, 0.7193, 0.2345),
    ("v1.2.0", 21, 0.7611, 0.2612, 0.6427, 0.1500),
    ("v1.2.1", 21, 0.7900, 0.2669, 0.6423, 0.1677),
    ("v1.3.0", 21, 0.6522, 0.2298, 0.6585, 0.0340),
    ("v1.4.0", 21, 0.6584, 0.2317, 0.6551, 0.0263),
    ("v1.4.1", 21, 0.6553, 0.2312, 0.6542, 0.0363),
    ("v1.5.0", 21, 0.6550, 0.2311, 0.6497, 0.0243),
    ("v1.6.0", 21, 0.6553, 0.2312, 0.6542, 0.0363),
    ("v2.0.0", 33, 0.6855, 0.2430, 0.6462, 0.0925),
    ("v2.1.0", 33, 0.6857, 0.2420, 0.6511, 0.0839),
    ("v2.2.0", 33, 0.7241, 0.2409, 0.6510, 0.0792),
    ("v3.0.0", 47, 0.6127, 0.2123, 0.7188, 0.0353),
    ("v3.1.0", 52, 0.6174, 0.2146, 0.7096, 0.0245),
]


def _load_versions():
    """Carga la tabla canónica desde el JSON; si falta, usa el respaldo."""
    if CANONICAL_JSON.exists():
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        rows = [(v["version"], v["n_features"], v["log_loss"], v["brier_score"],
                 v["roc_auc"], v["ece"]) for v in data["versiones"]]
        print(f"  Fuente: {CANONICAL_JSON.name} ({len(rows)} versiones)")
        return rows
    print("  Aviso: canonical_versions.json no encontrado; usando tabla de respaldo.")
    return _FALLBACK


VERSIONS = _load_versions()

# Anotaciones de hitos sobre las curvas
HIGHLIGHTS = {
    "v1.6.0": "Activo (documento)",
    "v2.2.0": "Bivariate Poisson",
    "v3.1.0": "Activo producción",
}

# ── Drift: Tabla 4.4 del documento + recuperación con v3.1.0 ─────────────────
# (versión, log_loss_publicado, log_loss_reciente, ece_publicado, ece_reciente)
DRIFT = [
    ("v1.6.0", 0.6553, 0.6926, 0.0363, 0.0844),  # se degrada
    ("v3.1.0", 0.6174, 0.6174, 0.0245, 0.0245),  # entrenado incl. 2025-26
]


def _passes(key, value):
    if value is None:
        return None
    spec = CRITERIA[key]
    return value < spec["threshold"] if spec["op"] == "<" else value > spec["threshold"]


def _color_for(key, value):
    ok = _passes(key, value)
    return INDIGO if ok else RED if ok is False else GRAY


# ════════════════════════════════════════════════════════════════════════════
# Figura 1 — Evolución de las 4 métricas
# ════════════════════════════════════════════════════════════════════════════
def plot_metrics_evolution(output_path):
    versions = [r[0] for r in VERSIONS]
    keys = ["log_loss", "brier_score", "roc_auc", "ece"]
    col_idx = {"log_loss": 2, "brier_score": 3, "roc_auc": 4, "ece": 5}

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    for ax, key in zip(axes.flatten(), keys):
        spec = CRITERIA[key]
        values = [r[col_idx[key]] for r in VERSIONS]
        colors = [_color_for(key, v) for v in values]

        ax.plot(versions, values, "-", color=NAVY, linewidth=1.6, alpha=0.45, zorder=1)
        ax.scatter(versions, values, c=colors, s=90, zorder=3,
                   edgecolor=WHITE, linewidth=1.2)
        ax.axhline(spec["threshold"], color=GRAY, linestyle="--", linewidth=1.3,
                   label=f"Criterio: {spec['op']} {spec['threshold']}")

        for vname, descr in HIGHLIGHTS.items():
            if vname in versions:
                i = versions.index(vname)
                ax.annotate(vname, xy=(i, values[i]), xytext=(0, 13),
                            textcoords="offset points", ha="center",
                            fontsize=8, fontweight="bold", color=NAVY,
                            bbox=dict(boxstyle="round,pad=0.3", fc=WHITE,
                                      ec=INDIGO, alpha=0.95))

        ax.set_title(spec["label"].upper(), fontsize=13, fontweight="bold")
        ax.set_xlabel("Versión", fontsize=10)
        ax.set_ylabel(spec["label"], fontsize=10)
        ax.tick_params(axis="x", rotation=45, labelsize=8.5)
        ax.tick_params(axis="y", labelsize=9)
        ax.grid(True, alpha=0.22, color=GRAY)
        ax.legend(loc="best", fontsize=9)

    fig.suptitle("EVOLUCIÓN DE MÉTRICAS PREDICTIVAS A LO LARGO DEL VERSIONADO (v1.0.0 → v3.1.0)",
                 fontsize=14, fontweight="bold", y=1.0)
    legend = [
        Patch(facecolor=INDIGO, edgecolor=WHITE, label="Pasa criterio"),
        Patch(facecolor=RED, edgecolor=WHITE, label="Falla criterio"),
        Patch(facecolor=GRAY, edgecolor=WHITE, label="Sin dato"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, fontsize=10,
               bbox_to_anchor=(0.5, -0.02))
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {output_path}")


# ════════════════════════════════════════════════════════════════════════════
# Figura 2 — Heatmap de cumplimiento por versión y métrica
# ════════════════════════════════════════════════════════════════════════════
def plot_criteria_heatmap(output_path):
    """Mapa de cumplimiento estilo tabla: FONDO BLANCO con el valor de cada
    métrica en color según su estado (índigo = pasa, rojo = falla). Rejilla
    gris. Sin bloques de color con texto blanco — el color va en la letra."""
    versions = [r[0] for r in VERSIONS]
    keys = ["log_loss", "brier_score", "roc_auc", "ece"]
    labels = [CRITERIA[k]["label"].upper() for k in keys]
    col_idx = {"log_loss": 2, "brier_score": 3, "roc_auc": 4, "ece": 5}

    nrows, ncols = len(keys), len(versions)
    fig, ax = plt.subplots(figsize=(max(9, ncols * 0.78), 4.4))
    ax.set_xlim(-0.5, ncols - 0.5); ax.set_ylim(-0.5, nrows - 0.5)
    ax.invert_yaxis()

    # Rejilla gris
    for i in range(nrows + 1):
        ax.axhline(i - 0.5, color=GRAY, linewidth=0.8, alpha=0.5)
    for j in range(ncols + 1):
        ax.axvline(j - 0.5, color=GRAY, linewidth=0.8, alpha=0.5)

    # Valores en color según estado, sobre fondo blanco
    for j, r in enumerate(VERSIONS):
        for i, k in enumerate(keys):
            v = r[col_idx[k]]
            ok = _passes(k, v)
            col = INDIGO if ok else RED if ok is False else GRAY
            ax.text(j, i, f"{v:.3f}", ha="center", va="center",
                    color=col, fontsize=8.6, fontweight="bold")

    ax.set_xticks(range(ncols))
    ax.set_xticklabels(versions, rotation=45, ha="right", fontsize=9, fontweight="bold")
    ax.set_yticks(range(nrows))
    ax.set_yticklabels(labels, fontsize=11, fontweight="bold")
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_color(GRAY)
    ax.set_title("MAPA DE CUMPLIMIENTO DE CRITERIOS POR VERSIÓN",
                 fontsize=13, fontweight="bold", pad=12)
    legend = [
        Patch(facecolor=WHITE, edgecolor=INDIGO, label="Pasa (texto índigo)"),
        Patch(facecolor=WHITE, edgecolor=RED, label="Falla (texto rojo)"),
    ]
    ax.legend(handles=legend, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=9.5, frameon=False)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {output_path}")


# ════════════════════════════════════════════════════════════════════════════
# Figura 3 — Tamaño del feature set vs Log Loss
# ════════════════════════════════════════════════════════════════════════════
def plot_feature_vs_logloss(output_path):
    fig, ax = plt.subplots(figsize=(11, 6.5))
    xs = [r[1] for r in VERSIONS]
    ys = [r[2] for r in VERSIONS]
    versions = [r[0] for r in VERSIONS]
    colors = [_color_for("log_loss", r[2]) for r in VERSIONS]

    # Trayectoria temporal
    for i in range(len(VERSIONS) - 1):
        ax.annotate("", xy=(xs[i + 1], ys[i + 1]), xytext=(xs[i], ys[i]),
                    arrowprops=dict(arrowstyle="->", color=GRAY, alpha=0.55, lw=1.4))
    ax.scatter(xs, ys, c=colors, s=140, zorder=3, edgecolor=WHITE, linewidth=1.4)
    ax.axhline(0.68, color=GRAY, linestyle="--", linewidth=1.3, label="Criterio Log Loss < 0,68")

    for x, y, v in zip(xs, ys, versions):
        if v in HIGHLIGHTS or v in ("v1.0.0", "v3.0.0"):
            ax.annotate(v, xy=(x, y), xytext=(6, 8), textcoords="offset points",
                        fontsize=9, fontweight="bold", color=NAVY)

    ax.set_xlabel("Número de features", fontsize=12)
    ax.set_ylabel("Log Loss", fontsize=12)
    ax.set_title("RELACIÓN ENTRE TAMAÑO DEL FEATURE SET Y LOG LOSS",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.22, color=GRAY)
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {output_path}")


# ════════════════════════════════════════════════════════════════════════════
# Figura 4 — Data drift: degradación de v1.6.0 vs recuperación de v3.1.0
# ════════════════════════════════════════════════════════════════════════════
def plot_drift_comparison(output_path):
    versions = [d[0] for d in DRIFT]
    x = np.arange(len(versions))
    w = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Log Loss
    ax1.bar(x - w / 2, [d[1] for d in DRIFT], w, label="Publicado", color=NAVY)
    ax1.bar(x + w / 2, [d[2] for d in DRIFT], w, label="Split 2025-26", color=RED)
    ax1.axhline(0.68, color=GRAY, linestyle="--", linewidth=1.3, label="Criterio < 0,68")
    ax1.set_title("LOG LOSS", fontsize=13, fontweight="bold")
    ax1.set_xticks(x); ax1.set_xticklabels(versions, fontsize=11)
    ax1.legend(fontsize=9); ax1.grid(True, axis="y", alpha=0.2, color=GRAY)
    for i, d in enumerate(DRIFT):
        ax1.text(i - w / 2, d[1] + 0.008, f"{d[1]:.4f}", ha="center", fontsize=8.5, color=NAVY)
        ax1.text(i + w / 2, d[2] + 0.008, f"{d[2]:.4f}", ha="center", fontsize=8.5, color=RED)

    # ECE
    ax2.bar(x - w / 2, [d[3] for d in DRIFT], w, label="Publicado", color=NAVY)
    ax2.bar(x + w / 2, [d[4] for d in DRIFT], w, label="Split 2025-26", color=RED)
    ax2.axhline(0.05, color=GRAY, linestyle="--", linewidth=1.3, label="Criterio < 0,05")
    ax2.set_title("ECE", fontsize=13, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels(versions, fontsize=11)
    ax2.legend(fontsize=9); ax2.grid(True, axis="y", alpha=0.2, color=GRAY)
    for i, d in enumerate(DRIFT):
        ax2.text(i - w / 2, d[3] + 0.002, f"{d[3]:.4f}", ha="center", fontsize=8.5, color=NAVY)
        ax2.text(i + w / 2, d[4] + 0.002, f"{d[4]:.4f}", ha="center", fontsize=8.5, color=RED)

    fig.suptitle("DATA DRIFT ESTACIONAL: v1.6.0 SE DEGRADA, v3.1.0 RECUPERA LOS CRITERIOS",
                 fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def main():
    ap = argparse.ArgumentParser(description="Figuras de versionado para la sustentación (hasta v3.1.0)")
    ap.add_argument("--output-dir", default=str(DEFAULT_FIG_DIR),
                    help="Directorio de salida (default: ML/reports/figures)")
    args = ap.parse_args()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)

    print("Generando figuras de versionado (paleta de sustentación)...")
    plot_metrics_evolution(out / "pres_version_evolution_metrics.png")
    plot_criteria_heatmap(out / "pres_version_criteria.png")
    plot_feature_vs_logloss(out / "pres_feature_vs_logloss.png")
    plot_drift_comparison(out / "pres_drift_comparison.png")
    print("Listo.")


if __name__ == "__main__":
    main()
