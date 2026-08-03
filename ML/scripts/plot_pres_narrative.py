"""
Gráficos narrativos para la SUSTENTACIÓN — reemplazan tablas por visuales.

Cuenta la historia técnica: problema → solución → desarrollo → validación →
resultados → aporte. Cinco figuras, paleta exclusiva, Arial, títulos en
MAYÚSCULA SOSTENIDA.

NO requiere Neon. Lee baselines desde reports/baselines_comparison_v3.json si
existe; si no, usa valores de respaldo. Totalmente reproducible.

Paleta: #B30016 rojo · #151A52 marino · #30308F índigo · #808080 gris · #FFFFFF blanco

Uso:
    cd ML
    python -m scripts.plot_pres_narrative
    python -m scripts.plot_pres_narrative --output-dir reports/figures/pres

Genera:
    pres_timeline.png             Línea de tiempo del versionado con hitos
    pres_feature_categories.png   Features agrupadas por categoría
    pres_results_comparison.png   v1.6.0 (2025-26) vs v3.1.0 en los 4 criterios
    pres_baselines_bar.png        Comparación horizontal vs líneas base
    pres_ensemble_flow.png        Flujo del ensemble: 3 señales → probabilidad
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

RED, NAVY, INDIGO, GRAY, WHITE = "#B30016", "#151A52", "#30308F", "#808080", "#FFFFFF"
SUBTLE = "#C7CBE8"  # texto secundario sobre marino (derivado, uso mínimo)

plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"],
    "axes.edgecolor": NAVY, "axes.labelcolor": NAVY, "text.color": NAVY,
    "xtick.color": NAVY, "ytick.color": NAVY, "axes.titlecolor": NAVY,
})

ML_ROOT = Path(__file__).parent.parent
FIG_DIR = ML_ROOT / "reports" / "figures"


def _card(ax, x, y, w, h, title, lines, fill=NAVY, tc=WHITE, ec="none",
          title_fs=12, body_fs=9.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.04",
                 fc=fill, ec=ec, lw=2.0 if ec != "none" else 0))
    ax.text(x + w / 2, y + h - 0.32, title, ha="center", va="top",
            color=tc, fontsize=title_fs, fontweight="bold")
    body_col = GRAY if fill == WHITE else SUBTLE
    ax.text(x + w / 2, y + h - 0.78, "\n".join(lines), ha="center", va="top",
            color=body_col, fontsize=body_fs, linespacing=1.45)


# ════════════════════════════════════════════════════════════════════════════
# FIGURA A — Línea de tiempo del versionado con hitos
# ════════════════════════════════════════════════════════════════════════════
def plot_timeline(out_path):
    fig, ax = plt.subplots(figsize=(13.2, 6.2), dpi=200)
    ax.set_xlim(0, 13.2); ax.set_ylim(0, 6.2); ax.axis("off")

    y0 = 3.1
    x_lo, x_hi = 0.8, 12.4
    # Bandas de régimen
    regimes = [
        (x_lo, 3.2, "EXPLORACIÓN", "v1.0.0 – v1.2.1", GRAY),
        (3.2, 6.0, "ESTABILIZACIÓN", "v1.3.0 – v1.6.0", INDIGO),
        (6.0, 8.9, "EXTENSIÓN", "v2.0.0 – v2.2.0", GRAY),
        (8.9, x_hi, "PRODUCCIÓN", "v3.0.0 – v3.1.0", NAVY),
    ]
    for xa, xb, name, rng, col in regimes:
        ax.add_patch(FancyBboxPatch((xa + 0.03, y0 - 0.28), xb - xa - 0.06, 0.56,
                     boxstyle="round,pad=0.0,rounding_size=0.05", fc=col, ec="none", alpha=0.16))
        ax.text((xa + xb) / 2, y0 + 0.62, name, ha="center", fontsize=10.5,
                fontweight="bold", color=col if col != GRAY else NAVY)
        ax.text((xa + xb) / 2, y0 - 0.62, rng, ha="center", fontsize=8.8, color=GRAY)

    # Eje temporal
    ax.annotate("", xy=(x_hi + 0.1, y0), xytext=(x_lo - 0.1, y0),
                arrowprops=dict(arrowstyle="-|>", lw=2.4, color=NAVY))

    # Hitos: (x, "arriba"/"abajo", color, título, detalle)
    milestones = [
        (1.5, "up", RED, "LEAKAGE DETECTADO", "AUC 0,85 · ECE 0,22\ncorregido en el pipeline"),
        (4.6, "down", INDIGO, "CALIBRACIÓN LOGRADA", "v1.3.0: 4/4 criterios\nECE baja a 0,034"),
        (5.6, "up", INDIGO, "BASELINE DOCUMENTO", "v1.6.0: modelo\nadoptado en el TG"),
        (7.4, "down", NAVY, "BIVARIATE POISSON", "v2.1.0–v2.2.0\nablation: sin valor neto"),
        (10.9, "up", INDIGO, "MODELO ACTIVO", "v3.1.0 · 52 features\nECE 0,024 · 4/4 ✓"),
    ]
    for x, side, col, title, detail in milestones:
        yb = y0 + 0.42 if side == "up" else y0 - 0.42
        yt = y0 + 1.05 if side == "up" else y0 - 1.05
        va = "bottom" if side == "up" else "top"
        ax.plot([x, x], [y0, yb], color=col, lw=1.6)
        ax.scatter([x], [y0], s=90, color=col, zorder=5, edgecolor=WHITE, linewidth=1.4)
        ax.text(x, yt, title, ha="center", va=va, fontsize=10, fontweight="bold", color=col)
        dy = yt + 0.02 if side == "up" else yt - 0.02
        ax.text(x, dy + (0.30 if side == "up" else -0.30), detail, ha="center", va=va,
                fontsize=8.4, color=GRAY, linespacing=1.3)

    ax.text(6.6, 5.85, "TRAYECTORIA DEL MODELO: 16 VERSIONES EN CUATRO REGÍMENES",
            ha="center", fontsize=13.5, fontweight="bold", color=NAVY)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


# ════════════════════════════════════════════════════════════════════════════
# FIGURA B — Features agrupadas por categoría
# ════════════════════════════════════════════════════════════════════════════
def plot_feature_categories(out_path):
    fig, ax = plt.subplots(figsize=(13.0, 6.6), dpi=200)
    ax.set_xlim(0, 13.0); ax.set_ylim(0, 6.6); ax.axis("off")

    # Hub
    ax.add_patch(FancyBboxPatch((5.1, 5.35), 2.8, 0.95, boxstyle="round,pad=0.02,rounding_size=0.08",
                 fc=NAVY, ec="none"))
    ax.text(6.5, 5.96, "52 FEATURES", ha="center", va="center", color=WHITE,
            fontsize=15, fontweight="bold")
    ax.text(6.5, 5.60, "shift(1) · sin fuga de información", ha="center", va="center",
            color=SUBTLE, fontsize=9)

    cats = [
        ("RENDIMIENTO", ["Puntos, off/def rating, pace", "eFG%, FG% / 3P% / FT% rolling",
                          "Rebotes, asistencias, pérdidas"], INDIGO),
        ("CONTEXTO FÍSICO", ["Días de descanso", "Back-to-back / descanso óptimo",
                             "Lesiones activas del plantel"], NAVY),
        ("FUERZA RELATIVA", ["Rating ELO (K=20)", "Win rate últimos 10",
                             "Strength composite"], NAVY),
        ("FORMA Y MATCHUP", ["Racha de victorias/derrotas", "Split local / visitante",
                             "Head-to-head últimos 5"], INDIGO),
    ]
    xs = [0.55, 3.68, 6.81, 9.94]
    w, h, y = 2.85, 3.0, 1.35
    for x, (name, items, col) in zip(xs, cats):
        _card(ax, x, y, w, h, name, ["• " + it for it in items], fill=col,
              title_fs=12.5, body_fs=9.6)
        # conector al hub
        ax.add_patch(FancyArrowPatch((x + w / 2, y + h + 0.02), (6.5, 5.33),
                     arrowstyle="-", lw=1.3, color=GRAY, alpha=0.6))

    ax.text(6.5, 0.75, "+ 2 features de MERCADO: probabilidades implícitas de las cuotas (sin vig)",
            ha="center", fontsize=10, style="italic", color=GRAY)
    ax.text(6.5, 6.42, "LAS 52 VARIABLES SE AGRUPAN EN CUATRO FAMILIAS DE RAZONAMIENTO",
            ha="center", fontsize=13, fontweight="bold", color=NAVY)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


# ════════════════════════════════════════════════════════════════════════════
# FIGURA C — Resultados: v1.6.0 (2025-26) vs v3.1.0 en los 4 criterios
# ════════════════════════════════════════════════════════════════════════════
def plot_results_comparison(out_path):
    # (métrica, umbral, "menor mejor", v1.6.0 reciente, v3.1.0)
    data = [
        ("LOG LOSS", 0.68, True, 0.6926, 0.6174),
        ("BRIER", 0.25, True, 0.2409, 0.2146),
        ("ROC-AUC", 0.55, False, 0.6510, 0.7096),
        ("ECE", 0.05, True, 0.0844, 0.0245),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(13.4, 4.4), dpi=200)
    for ax, (name, thr, lower, v160, v310) in zip(axes, data):
        vals = [v160, v310]
        labels = ["v1.6.0\n(2025-26)", "v3.1.0"]
        def ok(v): return v < thr if lower else v > thr
        colors = [INDIGO if ok(v) else RED for v in vals]
        bars = ax.bar([0, 1], vals, width=0.62, color=colors, edgecolor=WHITE, linewidth=1.2)
        ax.axhline(thr, color=GRAY, ls="--", lw=1.4)
        ax.text(1.5, thr, f"umbral {thr:g}", ha="right", va="bottom", fontsize=8, color=GRAY)
        for xb, v in zip([0, 1], vals):
            ax.text(xb, v + max(vals) * 0.03, f"{v:.4f}", ha="center", fontsize=9,
                    fontweight="bold", color=INDIGO if ok(v) else RED)
        ax.set_xticks([0, 1]); ax.set_xticklabels(labels, fontsize=9)
        ax.set_title(name, fontsize=12, fontweight="bold")
        ax.set_ylim(0, max(vals) * 1.28)
        ax.grid(True, axis="y", alpha=0.2, color=GRAY)
        for sp in ax.spines.values(): sp.set_color(GRAY)
        ax.tick_params(length=0)
    fig.suptitle("RESULTADOS SOBRE 2025-26: v1.6.0 FALLA DOS CRITERIOS, v3.1.0 LOS CUMPLE TODOS",
                 fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


# ════════════════════════════════════════════════════════════════════════════
# FIGURA D — Comparación horizontal contra líneas base
# ════════════════════════════════════════════════════════════════════════════
_BASE_FALLBACK = [
    ("Siempre local", 0.4754, "base"),
    ("Moneda al aire", 0.4754, "base"),
    ("Tasa fija de localía", 0.4754, "base"),
    ("XGBoost clasificador", 0.5896, "model"),
    ("Regresión logística", 0.6029, "model"),
    ("Random Forest solo", 0.6149, "model"),
    ("Ensemble", 0.6255, "ensemble"),
]


def _load_baselines():
    p = ML_ROOT / "reports" / "baselines_comparison_v3.json"
    if not p.exists():
        return _BASE_FALLBACK
    rows = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for r in rows:
        name = r.get("model", r.get("split", "?"))
        acc = r.get("accuracy")
        kind = "ensemble" if "nsemble" in name else ("base" if r.get("roc_auc", 1) == 0.5 else "model")
        out.append((name, acc, kind))
    return out


def plot_baselines_bar(out_path):
    rows = sorted(_load_baselines(), key=lambda r: r[1])
    names = [r[0] for r in rows]
    accs = [r[1] for r in rows]
    cmap = {"base": GRAY, "model": NAVY, "ensemble": INDIGO}
    colors = [cmap[r[2]] for r in rows]

    fig, ax = plt.subplots(figsize=(11.6, 5.0), dpi=200)
    y = np.arange(len(names))
    ax.barh(y, accs, color=colors, edgecolor=WHITE, linewidth=1.2, height=0.66)
    for yi, a in zip(y, accs):
        ax.text(a + 0.006, yi, f"{a*100:.1f} %", va="center", fontsize=10,
                fontweight="bold", color=NAVY)
    ax.axvline(0.5, color=RED, ls="--", lw=1.4)
    ax.text(0.5, len(names) - 0.3, "azar (50 %)", color=RED, fontsize=9, ha="center")
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=11)
    ax.set_xlim(0.40, 0.70)
    ax.set_xlabel("Accuracy sobre el conjunto de prueba (n = 753)", fontsize=11)
    ax.set_title("EL ENSEMBLE SUPERA A CADA MODELO INDIVIDUAL Y A LAS LÍNEAS BASE",
                 fontsize=12.5, fontweight="bold", pad=12)
    ax.grid(True, axis="x", alpha=0.2, color=GRAY)
    for sp in ax.spines.values(): sp.set_color(GRAY)
    ax.tick_params(length=0)
    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


# ════════════════════════════════════════════════════════════════════════════
# FIGURA E — Flujo del ensemble: 3 señales distintas → probabilidad calibrada
# ════════════════════════════════════════════════════════════════════════════
def plot_ensemble_flow(out_path):
    fig, ax = plt.subplots(figsize=(13.0, 6.6), dpi=200)
    ax.set_xlim(0, 13.0); ax.set_ylim(0, 6.6); ax.axis("off")

    # Columna 1 — modelos base con su TIPO de señal
    base = [
        ("RANDOM FOREST", "calibrado", "SEÑAL: probabilidad\ndiscriminativa", "rf_proba"),
        ("XGBOOST DUAL", "home / away", "SEÑAL: magnitud\ndel marcador", "score_diff"),
        ("BIVARIATE POISSON", "Karlis-Ntzoufras", "SEÑAL: estructura\ne incertidumbre", "μ_diff, σ_diff"),
    ]
    bx, bw, bh = 0.5, 3.5, 1.5
    ys = [4.55, 2.55, 0.55]
    for (t, sub, sig, out), y in zip(base, ys):
        ax.add_patch(FancyBboxPatch((bx, y), bw, bh, boxstyle="round,pad=0.02,rounding_size=0.05",
                     fc=NAVY, ec="none"))
        ax.text(bx + bw / 2, y + bh - 0.30, t, ha="center", va="top", color=WHITE,
                fontsize=12, fontweight="bold")
        ax.text(bx + bw / 2, y + bh - 0.62, sub, ha="center", va="top", color=SUBTLE, fontsize=8.6)
        ax.text(bx + bw / 2, y + 0.42, sig, ha="center", va="center", color=INDIGO_TEXT if False else "#AEB3E0",
                fontsize=9, fontweight="bold", linespacing=1.2)
        ax.text(bx + bw + 0.12, y + bh / 2, out, ha="left", va="center", color=NAVY,
                fontsize=9.5, fontweight="bold", style="italic")

    # Columna 2 — meta-learner
    mx, mw, mh, my = 6.7, 3.0, 2.2, 2.2
    ax.add_patch(FancyBboxPatch((mx, my), mw, mh, boxstyle="round,pad=0.02,rounding_size=0.06",
                 fc=INDIGO, ec="none"))
    ax.text(mx + mw / 2, my + mh - 0.4, "META-LEARNER", ha="center", va="top", color=WHITE,
            fontsize=13, fontweight="bold")
    ax.text(mx + mw / 2, my + mh / 2 - 0.1,
            "StandardScaler +\nRegresión Logística\n(4 meta-features)",
            ha="center", va="center", color=WHITE, fontsize=10, linespacing=1.4)
    ax.text(mx + mw / 2, my + 0.28, "stacking OOF · K=5 temporal", ha="center", va="center",
            color=SUBTLE, fontsize=8.5)

    # Columna 3 — calibración + salida
    cx, cw, ch, cy = 10.4, 2.3, 2.2, 2.2
    ax.add_patch(FancyBboxPatch((cx, cy), cw, ch, boxstyle="round,pad=0.02,rounding_size=0.06",
                 fc=WHITE, ec=INDIGO, lw=2.4))
    ax.text(cx + cw / 2, cy + ch - 0.4, "CALIBRACIÓN\nISOTÓNICA", ha="center", va="top",
            color=NAVY, fontsize=12, fontweight="bold", linespacing=1.2)
    ax.text(cx + cw / 2, cy + ch / 2 - 0.15, "P(home_win)\ncalibrada", ha="center", va="center",
            color=INDIGO, fontsize=11, fontweight="bold", linespacing=1.3)
    ax.text(cx + cw / 2, cy + 0.30, "ECE 0,024", ha="center", va="center", color=RED, fontsize=10,
            fontweight="bold")

    # Flechas base → meta
    for y in ys:
        ax.add_patch(FancyArrowPatch((bx + bw + 1.05, y + bh / 2), (mx - 0.05, my + mh / 2),
                     arrowstyle="-|>", mutation_scale=18, lw=2.0, color=GRAY,
                     connectionstyle="arc3,rad=0.0"))
    ax.add_patch(FancyArrowPatch((mx + mw + 0.02, my + mh / 2), (cx - 0.05, cy + ch / 2),
                 arrowstyle="-|>", mutation_scale=20, lw=2.4, color=GRAY))

    ax.text(6.5, 6.35, "TRES SEÑALES COMPLEMENTARIAS SE FUSIONAN EN UNA PROBABILIDAD CALIBRADA",
            ha="center", fontsize=13, fontweight="bold", color=NAVY)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


INDIGO_TEXT = "#AEB3E0"


def main():
    ap = argparse.ArgumentParser(description="Gráficos narrativos para la sustentación")
    ap.add_argument("--output-dir", default=str(FIG_DIR))
    args = ap.parse_args()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)

    print("Generando gráficos narrativos (paleta exclusiva, Arial)...")
    plot_timeline(out / "pres_timeline.png")
    plot_feature_categories(out / "pres_feature_categories.png")
    plot_results_comparison(out / "pres_results_comparison.png")
    plot_baselines_bar(out / "pres_baselines_bar.png")
    plot_ensemble_flow(out / "pres_ensemble_flow.png")
    print("Listo.")


if __name__ == "__main__":
    main()
