"""
Backtesting de rentabilidad simulada - Ensemble v1.6.0

Simula tres estrategias de apuesta sobre el test set:
  1. Stake fijo con filtro EV (regla del model spec §5.2)
  2. Kelly fraccional (quarter-Kelly)
  3. Flat en todos los juegos (sin filtro)

Si no hay odds históricas suficientes (~1% cobertura),
genera odds simuladas con margen de vigorish típico.

Uso:
    cd ML
    python -m scripts.backtesting
"""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.train import (
    load_ml_ready_games,
    build_feature_matrix,
    TARGET,
    DATE_COL,
)
from src.evaluation.validation import temporal_train_test_split
from src.evaluation.metrics import (
    compute_expected_value,
    compute_kelly_fraction,
)


def generate_simulated_odds(y_test, home_win_rate, vig=0.05):
    """
    Genera odds decimales simuladas basadas en el home win rate histórico.

    Simula un mercado con margen de vigorish (vig) uniforme:
        odds_home = 1 / (home_win_rate + vig/2)
        odds_away = 1 / ((1 - home_win_rate) + vig/2)

    Agrega ruido para simular variación entre partidos.
    """
    rng = np.random.RandomState(42)
    n = len(y_test)

    # Probabilidad implícita del mercado (con vig)
    p_market_home = home_win_rate + vig / 2
    base_odds_home = 1.0 / p_market_home

    # Ruido: ±5% para simular variación entre partidos
    noise = rng.uniform(-0.05, 0.05, size=n)
    odds_home = base_odds_home * (1 + noise)

    # Asegurar odds razonables para NBA (1.10 a 5.00)
    odds_home = np.clip(odds_home, 1.10, 5.00)

    return odds_home


def run_strategy(name, y_test, y_proba, odds, bet_mask, stake_fn):
    """
    Ejecuta una estrategia de apuesta y retorna métricas.

    Args:
        name:      nombre de la estrategia
        y_test:    resultados reales
        y_proba:   probabilidades predichas
        odds:      cuotas decimales
        bet_mask:  booleano indicando qué juegos se apuestan
        stake_fn:  función(p, odds) → stake por apuesta
    """
    n_bets = int(bet_mask.sum())
    if n_bets == 0:
        return {
            "strategy": name, "n_bets": 0, "win_rate": 0.0,
            "roi": 0.0, "yield_per_bet": 0.0, "max_drawdown_pct": 0.0,
            "total_profit": 0.0, "total_staked": 0.0, "sharpe": 0.0,
            "profits_series": [],
        }

    y_bet = y_test[bet_mask]
    odds_bet = odds[bet_mask]
    proba_bet = y_proba[bet_mask]

    # Calcular stakes
    stakes = np.array([stake_fn(p, o) for p, o in zip(proba_bet, odds_bet)])

    # Ganancias por apuesta
    profits = np.where(y_bet == 1, stakes * (odds_bet - 1.0), -stakes)
    cumulative = np.cumsum(profits)

    total_staked = float(stakes.sum())
    total_profit = float(profits.sum())
    roi = total_profit / total_staked if total_staked > 0 else 0.0
    yield_per_bet = total_profit / n_bets
    win_rate = float(y_bet.mean())

    # Drawdown máximo
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = running_max - cumulative
    max_dd = float(drawdowns.max())
    max_dd_pct = max_dd / total_staked if total_staked > 0 else 0.0

    # Sharpe ratio (retornos por apuesta)
    returns = profits / stakes
    sharpe = float(returns.mean() / returns.std()) if returns.std() > 0 else 0.0

    return {
        "strategy": name,
        "n_bets": n_bets,
        "win_rate": round(win_rate, 4),
        "roi": round(roi, 4),
        "yield_per_bet": round(yield_per_bet, 4),
        "max_drawdown_pct": round(max_dd_pct, 4),
        "total_profit": round(total_profit, 4),
        "total_staked": round(total_staked, 4),
        "sharpe": round(sharpe, 4),
        "profits_series": [round(float(p), 4) for p in profits],
    }


def run_backtesting():
    # ------------------------------------------------------------------
    # 1. Cargar modelo y datos
    # ------------------------------------------------------------------
    df = load_ml_ready_games()
    X, y, feature_cols, df_clean = build_feature_matrix(df)
    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)

    X_test = df_test[feature_cols].values
    y_test = df_test[TARGET].astype(int).values

    # Cargar modelo v1.6.0
    model_path = Path(__file__).parent.parent / "models" / "nba_prediction_model_v1.6.0.joblib"
    if not model_path.exists():
        print(f"ERROR: No se encontró {model_path}")
        sys.exit(1)
    ensemble = joblib.load(model_path)
    y_proba = ensemble.predict_home_win_proba(X_test)

    # ------------------------------------------------------------------
    # 2. Obtener odds
    # ------------------------------------------------------------------
    implied = pd.to_numeric(
        df_test.get("implied_prob_home", pd.Series(dtype=float)),
        errors="coerce"
    ).values
    valid_odds = ~np.isnan(implied) & (implied > 0)
    n_real_odds = int(valid_odds.sum())

    if n_real_odds > len(y_test) * 0.10:  # >10% cobertura
        print(f"\nUsando odds reales ({n_real_odds}/{len(y_test)} juegos)")
        odds = np.where(valid_odds, 1.0 / implied, np.nan)
        using_simulated = False
    else:
        home_win_rate = float(df_train[TARGET].astype(int).mean())
        print(f"\n[!] ADVERTENCIA: Solo {n_real_odds}/{len(y_test)} juegos con odds reales.")
        print(f"    Generando odds simuladas (home_win_rate={home_win_rate:.4f}, vig=5%)")
        print(f"    Los resultados económicos son INDICATIVOS, no definitivos.\n")
        odds = generate_simulated_odds(y_test, home_win_rate, vig=0.05)
        using_simulated = True

    # ------------------------------------------------------------------
    # 3. Calcular EV por juego
    # ------------------------------------------------------------------
    ev = np.array([compute_expected_value(p, o) for p, o in zip(y_proba, odds)])

    # ------------------------------------------------------------------
    # 4. Ejecutar estrategias
    # ------------------------------------------------------------------
    strategies = []

    # Estrategia 1: Stake fijo con filtro EV (model spec §5.2)
    mask_ev = (ev > 0.05) & (y_proba > 0.55)
    strategies.append(run_strategy(
        "Stake fijo (EV>0.05, P>0.55)",
        y_test, y_proba, odds, mask_ev,
        stake_fn=lambda p, o: 1.0,
    ))

    # Estrategia 2: Kelly fraccional (quarter-Kelly) con mismo filtro
    strategies.append(run_strategy(
        "Kelly fraccional (25%)",
        y_test, y_proba, odds, mask_ev,
        stake_fn=lambda p, o: compute_kelly_fraction(p, o, fraction=0.25),
    ))

    # Estrategia 3: Flat en todos (sin filtro)
    mask_all = np.ones(len(y_test), dtype=bool)
    strategies.append(run_strategy(
        "Flat en todos",
        y_test, y_proba, odds, mask_all,
        stake_fn=lambda p, o: 1.0,
    ))

    # ------------------------------------------------------------------
    # 5. Imprimir resultados
    # ------------------------------------------------------------------
    print("\n" + "=" * 95)
    print("  BACKTESTING DE RENTABILIDAD - Ensemble v1.6.0")
    if using_simulated:
        print("  (Odds simuladas - resultados indicativos)")
    print("=" * 95)
    header = (
        f"  {'Estrategia':<32} {'N':>5} {'Win%':>7} {'ROI':>8} "
        f"{'Yield':>8} {'MaxDD%':>8} {'Sharpe':>8} {'Profit':>10}"
    )
    print(header)
    print("  " + "-" * 91)

    for s in strategies:
        print(
            f"  {s['strategy']:<32} {s['n_bets']:>5} {s['win_rate']:>7.2%} "
            f"{s['roi']:>8.2%} {s['yield_per_bet']:>8.4f} {s['max_drawdown_pct']:>8.2%} "
            f"{s['sharpe']:>8.4f} {s['total_profit']:>+10.2f}"
        )

    print("=" * 95)

    # ------------------------------------------------------------------
    # 6. Guardar resultados
    # ------------------------------------------------------------------
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    output_path = reports_dir / "backtesting_results.json"

    output = {
        "model_version": "v1.6.0",
        "test_size": len(y_test),
        "using_simulated_odds": using_simulated,
        "n_real_odds": n_real_odds,
        "strategies": [
            {k: v for k, v in s.items()}
            for s in strategies
        ],
        "ev_distribution": {
            "mean": round(float(ev.mean()), 4),
            "std": round(float(ev.std()), 4),
            "min": round(float(ev.min()), 4),
            "max": round(float(ev.max()), 4),
            "pct_positive": round(float((ev > 0).mean()), 4),
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=float)

    print(f"\n  Resultados guardados: {output_path}")


if __name__ == "__main__":
    run_backtesting()
