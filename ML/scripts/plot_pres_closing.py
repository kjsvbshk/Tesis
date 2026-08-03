"""
Gráficos de cierre y objetivos para la SUSTENTACIÓN — reemplazan tablas por
visuales insertables en la plantilla UMB.

Cuatro figuras, paleta exclusiva, Arial, títulos en MAYÚSCULA SOSTENIDA.
NO requiere Neon ni datos: son esquemas. Totalmente reproducible.

Uso:
    cd ML
    python -m scripts.plot_pres_closing

Genera:
    pres_objetivos.png          Objetivos específicos como hoja de ruta (slide 7)
    pres_aportes.png            Tres aportes del trabajo con su evidencia (9.1)
    pres_cumplimiento.png       Cumplimiento de los 6 OE (checklist, 9.2)
    pres_trabajo_futuro.png     Cinco líneas de trabajo futuro con estado (9.3)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

RED, NAVY, INDIGO, GRAY, WHITE = "#B30016", "#151A52", "#30308F", "#808080", "#FFFFFF"
SUBTLE = "#C7CBE8"
plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"],
    "text.color": NAVY, "axes.edgecolor": NAVY,
})
FIG_DIR = Path(__file__).parent.parent / "reports" / "figures"


# ════════════════════════════════════════════════════════════════════════════
# FIG 1 — Objetivos específicos como hoja de ruta (reemplaza tabla del slide 7)
# ════════════════════════════════════════════════════════════════════════════
def plot_objetivos(out_path):
    fig, ax = plt.subplots(figsize=(13.0, 6.4), dpi=200)
    ax.set_xlim(0, 13.0); ax.set_ylim(0, 6.4); ax.axis("off")

    phases = [
        ("INVESTIGAR", ["OE1  Métodos de ML\npara eventos discretos"], INDIGO),
        ("DISEÑAR", ["OE2  Base de datos\nhistórica y de cuotas",
                     "OE3  Interfaz usable\npara el apostador"], NAVY),
        ("IMPLEMENTAR", ["OE4  Modelos y su\ncapacidad predictiva",
                         "OE5  Backend de\npredicción"], NAVY),
        ("EVALUAR", ["OE6  Desempeño con\npruebas experimentales"], INDIGO),
    ]
    xs = [0.55, 3.68, 6.81, 9.94]
    w = 2.85
    for idx, (x, (phase, cards, col)) in enumerate(zip(xs, phases)):
        # etiqueta de fase
        ax.add_patch(FancyBboxPatch((x, 5.25), w, 0.7, boxstyle="round,pad=0.02,rounding_size=0.1",
                     fc=col, ec="none"))
        ax.text(x + w / 2, 5.6, phase, ha="center", va="center", color=WHITE,
                fontsize=13, fontweight="bold")
        # tarjetas de OE
        n = len(cards)
        ch = 1.55 if n == 1 else 1.55
        gap = 0.35
        total = n * ch + (n - 1) * gap
        y_start = 4.55
        for j, card in enumerate(cards):
            y = y_start - j * (ch + gap) - ch
            ax.add_patch(FancyBboxPatch((x, y), w, ch, boxstyle="round,pad=0.02,rounding_size=0.05",
                         fc=WHITE, ec=col, lw=2.2))
            oe, desc = card.split("  ", 1)
            ax.text(x + w / 2, y + ch - 0.34, oe, ha="center", va="top", color=col,
                    fontsize=13, fontweight="bold")
            ax.text(x + w / 2, y + ch - 0.78, desc.split("  ", 1)[-1] if "  " in desc else desc,
                    ha="center", va="top", color=NAVY, fontsize=9.6, linespacing=1.3)
        # flecha a la siguiente fase
        if idx < 3:
            ax.add_patch(FancyArrowPatch((x + w + 0.02, 5.6), (xs[idx + 1] - 0.02, 5.6),
                         arrowstyle="-|>", mutation_scale=18, lw=2.0, color=GRAY))

    ax.text(6.5, 6.15, "SEIS OBJETIVOS ESPECÍFICOS: DEL ESTUDIO A LA EVALUACIÓN EXPERIMENTAL",
            ha="center", fontsize=13, fontweight="bold", color=NAVY)
    ax.text(6.5, 0.6, "Objetivo general: desarrollar un prototipo funcional web de predicción "
            "deportiva con machine learning", ha="center", fontsize=10, style="italic", color=GRAY)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


# ════════════════════════════════════════════════════════════════════════════
# FIG 2 — Tres aportes del trabajo con su evidencia (9.1)
# ════════════════════════════════════════════════════════════════════════════
def plot_aportes(out_path):
    fig, ax = plt.subplots(figsize=(13.0, 6.4), dpi=200)
    ax.set_xlim(0, 13.0); ax.set_ylim(0, 6.4); ax.axis("off")

    cards = [
        ("SISTEMA EN\nPRODUCCIÓN",
         ["Ensemble v3.1.0 desplegado", "(Vercel + Render)", "",
          "52 features · ECE 0,024", "4/4 criterios cumplidos", "",
          "Verificado extremo a extremo:", "registro, 2FA, predicción,", "apuesta y créditos"], INDIGO),
        ("RIGOR\nMETODOLÓGICO",
         ["Protocolo anti-leakage:", "split temporal, shift(1),", "stacking out-of-fold", "",
          "El propio protocolo detectó", "y corrigió el leakage de v1.0.0", "(AUC 0,85 · ECE 0,22)"], NAVY),
        ("CONTRIBUCIONES\nCIENTÍFICAS",
         ["Resultado negativo del", "Bivariate Poisson en NBA", "(ablation de 8 variantes)", "",
          "Data drift estacional como", "fenómeno medible y corregido", "por reentrenamiento"], INDIGO),
    ]
    xs = [0.6, 4.7, 8.8]
    w, h, y = 3.6, 4.5, 0.9
    for x, (title, lines, col) in zip(xs, cards):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.04",
                     fc=col, ec="none"))
        ax.text(x + w / 2, y + h - 0.42, title, ha="center", va="top", color=WHITE,
                fontsize=14, fontweight="bold", linespacing=1.15)
        ax.text(x + w / 2, y + h - 1.55, "\n".join(lines), ha="center", va="top",
                color=WHITE, fontsize=10, linespacing=1.4)

    ax.text(6.5, 6.1, "TRES APORTES DEL TRABAJO, MÁS ALLÁ DEL PROTOTIPO",
            ha="center", fontsize=13.5, fontweight="bold", color=NAVY)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


# ════════════════════════════════════════════════════════════════════════════
# FIG 3 — Cumplimiento de los 6 OE (checklist, 9.2)
# ════════════════════════════════════════════════════════════════════════════
def plot_cumplimiento(out_path):
    fig, ax = plt.subplots(figsize=(13.0, 6.2), dpi=200)
    ax.set_xlim(0, 13.0); ax.set_ylim(0, 6.2); ax.axis("off")

    items = [
        ("OE1", "Investigar métodos de ML", "Marco teórico: RF, XGBoost y Bivariate Poisson justificados"),
        ("OE2", "Diseñar la base de datos", "PostgreSQL en Neon, normalizado a 3FN, tres schemas por dominio"),
        ("OE3", "Diseñar la interfaz", "Frontend React 19 desplegado, con predicciones y apuestas virtuales"),
        ("OE4", "Implementar y evaluar modelos", "16 versiones evaluadas con Log Loss, Brier, ROC-AUC y ECE"),
        ("OE5", "Implementar el backend", "FastAPI sirviendo el modelo activo con autenticación y auditoría"),
        ("OE6", "Evaluar con pruebas tabuladas", "Ablation study, líneas base, backtesting y diagnóstico de drift"),
    ]
    y0 = 5.05
    dy = 0.78
    for i, (oe, title, ev) in enumerate(items):
        y = y0 - i * dy
        # check índigo
        ax.add_patch(plt.Circle((0.75, y), 0.19, color=INDIGO, zorder=3))
        ax.text(0.75, y - 0.015, "✓", ha="center", va="center", color=WHITE,
                fontsize=13, fontweight="bold", zorder=4)
        ax.text(1.15, y + 0.12, f"{oe}  ·  {title}", ha="left", va="center",
                color=NAVY, fontsize=12.5, fontweight="bold")
        ax.text(1.15, y - 0.20, ev, ha="left", va="center", color=GRAY, fontsize=10.3)
        if i < len(items) - 1:
            ax.plot([0.75, 0.75], [y - 0.19, y - dy + 0.19], color=SUBTLE, lw=1.5, zorder=1)

    ax.text(0.55, 5.85, "LOS SEIS OBJETIVOS ESPECÍFICOS, CUBIERTOS CON EVIDENCIA",
            ha="left", fontsize=13.5, fontweight="bold", color=NAVY)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


# ════════════════════════════════════════════════════════════════════════════
# FIG 4 — Cinco líneas de trabajo futuro con estado (9.3)
# ════════════════════════════════════════════════════════════════════════════
def plot_trabajo_futuro(out_path):
    fig, ax = plt.subplots(figsize=(13.0, 6.2), dpi=200)
    ax.set_xlim(0, 13.0); ax.set_ylim(0, 6.2); ax.axis("off")

    items = [
        ("1", "Reentrenamiento por temporada NBA con reevaluación de criterios",
         "EJECUTADO — v3.1.0", INDIGO),
        ("2", "Sustituir el Bivariate Poisson por una Binomial Negativa Bivariada",
         "ABIERTO", GRAY),
        ("3", "Features dedicadas por estadística para los props de equipo",
         "ABIERTO", GRAY),
        ("4", "Saneamiento de targets con boxscores incompletos antes de entrenar",
         "ABIERTO", GRAY),
        ("5", "Explorar Beta calibration frente a la isotónica (>3 meta-features)",
         "ABIERTO", GRAY),
    ]
    y0 = 4.9
    dy = 0.86
    for i, (num, desc, status, col) in enumerate(items):
        y = y0 - i * dy
        ax.add_patch(FancyBboxPatch((0.55, y - 0.28), 0.62, 0.62,
                     boxstyle="round,pad=0.02,rounding_size=0.08", fc=col, ec="none"))
        ax.text(0.86, y + 0.04, num, ha="center", va="center", color=WHITE,
                fontsize=15, fontweight="bold")
        ax.text(1.45, y + 0.04, desc, ha="left", va="center", color=NAVY, fontsize=12)
        # etiqueta de estado a la derecha
        ax.add_patch(FancyBboxPatch((10.4, y - 0.24), 2.15, 0.5,
                     boxstyle="round,pad=0.02,rounding_size=0.1",
                     fc=(INDIGO if col == INDIGO else WHITE), ec=col, lw=1.8))
        ax.text(11.47, y + 0.02, status, ha="center", va="center",
                color=(WHITE if col == INDIGO else GRAY), fontsize=9.5, fontweight="bold")

    ax.text(0.55, 5.75, "TRABAJO FUTURO: LA PRIMERA LÍNEA YA FUE EJECUTADA Y VALIDADA",
            ha="left", fontsize=13.5, fontweight="bold", color=NAVY)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  Guardado: {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=str(FIG_DIR))
    args = ap.parse_args()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    print("Generando gráficos de cierre y objetivos...")
    plot_objetivos(out / "pres_objetivos.png")
    plot_aportes(out / "pres_aportes.png")
    plot_cumplimiento(out / "pres_cumplimiento.png")
    plot_trabajo_futuro(out / "pres_trabajo_futuro.png")
    print("Listo.")


if __name__ == "__main__":
    main()
