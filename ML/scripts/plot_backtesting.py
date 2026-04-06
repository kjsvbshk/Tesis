"""
Visualización de backtesting — Profit acumulado, drawdown y distribución EV.

Requiere ejecutar primero: python -m scripts.backtesting
(genera ML/reports/backtesting_results.json)

Uso:
    cd ML
    python -m scripts.plot_backtesting
"""

import sys
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPORTS_DIR = Path(__file__).parent.parent / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

COLORS = {
    "Stake fijo (EV>0.05, P>0.55)": "#2563EB",
    "Kelly fraccional (25%)": "#10B981",
    "Flat en todos": "#EF4444",
}


def load_backtesting_results():
    path = REPORTS_DIR / "backtesting_results_v3.json"
    if not path.exists():
        print(f"ERROR: No se encontró {path}")
        print("  Ejecuta primero: python -m scripts.backtesting")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_cumulative_profit(strategies, using_simulated, output_path):
    """Profit acumulado por estrategia."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for s in strategies:
        profits = s["profits_series"]
        if not profits:
            continue
        cumulative = np.cumsum(profits)
        color = COLORS.get(s["strategy"], "gray")
        label = f"{s['strategy']} (ROI={s['roi']:.2%})"
        ax.plot(cumulative, color=color, linewidth=1.5, label=label)

    ax.axhline(y=0, color="black", linewidth=0.8, alpha=0.3)
    ax.set_xlabel("Apuesta #", fontsize=12)
    ax.set_ylabel("Profit acumulado (unidades)", fontsize=12)
    title = "Profit acumulado — Ensemble v2.0.0"
    if using_simulated:
        title += " (odds simuladas)"
    ax.set_title(title, fontsize=14)
    ax.legend(fontsize=9, loc="best")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def plot_drawdown(strategies, using_simulated, output_path):
    """Drawdown por estrategia."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for s in strategies:
        profits = s["profits_series"]
        if not profits:
            continue
        cumulative = np.cumsum(profits)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max  # Siempre <= 0

        color = COLORS.get(s["strategy"], "gray")
        label = f"{s['strategy']} (MaxDD={s['max_drawdown_pct']:.2%})"
        ax.fill_between(range(len(drawdown)), drawdown, alpha=0.3, color=color)
        ax.plot(drawdown, color=color, linewidth=1, label=label)

    ax.axhline(y=0, color="black", linewidth=0.8, alpha=0.3)
    ax.set_xlabel("Apuesta #", fontsize=12)
    ax.set_ylabel("Drawdown (unidades)", fontsize=12)
    title = "Drawdown — Ensemble v2.0.0"
    if using_simulated:
        title += " (odds simuladas)"
    ax.set_title(title, fontsize=14)
    ax.legend(fontsize=9, loc="best")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def plot_ev_distribution(ev_stats, output_path):
    """Histograma de distribución de Expected Value."""
    fig, ax = plt.subplots(figsize=(8, 5))

    # Generar datos simulados de EV a partir de estadísticas
    rng = np.random.RandomState(42)
    ev_samples = rng.normal(ev_stats["mean"], ev_stats["std"], size=1000)
    ev_samples = np.clip(ev_samples, ev_stats["min"], ev_stats["max"])

    ax.hist(ev_samples, bins=40, color="#8B5CF6", alpha=0.7, edgecolor="white")
    ax.axvline(x=0, color="red", linestyle="--", alpha=0.7, label="EV = 0 (sin ventaja)")
    ax.axvline(x=0.05, color="green", linestyle="--", alpha=0.7, label="Umbral EV = 0.05")
    ax.axvline(x=ev_stats["mean"], color="blue", linestyle="-", alpha=0.7,
               label=f"Media EV = {ev_stats['mean']:.4f}")

    pct_pos = ev_stats["pct_positive"]
    ax.set_xlabel("Expected Value (EV)", fontsize=12)
    ax.set_ylabel("Frecuencia", fontsize=12)
    ax.set_title(f"Distribución de EV — {pct_pos:.0%} de juegos con EV > 0", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {output_path}")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    data = load_backtesting_results()
    strategies = data["strategies"]
    using_simulated = data["using_simulated_odds"]

    if using_simulated:
        print("[!] Nota: Las graficas usan odds simuladas (indicativo)")

    print("\nGenerando gráficas de backtesting...")

    plot_cumulative_profit(
        strategies, using_simulated,
        FIGURES_DIR / "cumulative_profit_v3.png",
    )

    plot_drawdown(
        strategies, using_simulated,
        FIGURES_DIR / "drawdown_v3.png",
    )

    plot_ev_distribution(
        data["ev_distribution"],
        FIGURES_DIR / "ev_distribution_v3.png",
    )

    print(f"\n  Todas las gráficas guardadas en: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
