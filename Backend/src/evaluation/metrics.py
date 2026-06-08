"""
Métricas de evaluación del modelo NBA.

Implementa todas las métricas requeridas por el model spec:

  Predictivas primarias:
    - Log Loss     (objetivo < 0.68)
    - Brier Score  (objetivo < 0.25)

  Predictivas secundarias:
    - ROC-AUC      (objetivo > 0.55)
    - Accuracy
    - ECE          (Expected Calibration Error, objetivo < 0.05)

  Económicas (backtesting):
    - Expected Value (EV)
    - ROI
    - Drawdown máximo
    - Win Rate
"""

import numpy as np
from sklearn.metrics import (
    log_loss,
    brier_score_loss,
    roc_auc_score,
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
)


# ---------------------------------------------------------------------------
# Métricas predictivas
# ---------------------------------------------------------------------------

def compute_log_loss(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """
    Log Loss — métrica de entrenamiento principal.
    Criterio de aceptación: < 0.68
    """
    return log_loss(y_true, y_proba)


def compute_brier_score(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """
    Brier Score — penaliza predicciones confiadas que están equivocadas.
    Criterio de aceptación: < 0.25
    Baseline (predictor naive 0.5): Brier = 0.25
    """
    return brier_score_loss(y_true, y_proba)


def compute_roc_auc(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """
    ROC-AUC — capacidad de discriminación.
    Criterio de aceptación: > 0.55
    Baseline (aleatorio): AUC = 0.50
    """
    return roc_auc_score(y_true, y_proba)


def compute_accuracy(y_true: np.ndarray, y_proba: np.ndarray, threshold: float = 0.5) -> float:
    """Accuracy con threshold configurable."""
    y_pred = (y_proba >= threshold).astype(int)
    return accuracy_score(y_true, y_pred)


def compute_ece(y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10) -> float:
    """
    Expected Calibration Error (ECE).

    Mide la diferencia entre la confianza predicha y la frecuencia real
    de victorias en cada bin de probabilidad.

    Criterio de aceptación: < 0.05
    Un ECE = 0 indica calibración perfecta.

    Args:
        y_true:  etiquetas reales (0/1)
        y_proba: probabilidades predichas P(home_win)
        n_bins:  número de bins de igual ancho en [0, 1]

    Returns:
        ECE como float en [0, 1]
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)

    for i in range(n_bins):
        mask = (y_proba >= bins[i]) & (y_proba < bins[i + 1])
        if mask.sum() == 0:
            continue
        bin_accuracy = y_true[mask].mean()
        bin_confidence = y_proba[mask].mean()
        bin_weight = mask.sum() / n
        ece += bin_weight * abs(bin_accuracy - bin_confidence)

    return ece


def evaluate_classifier(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    label: str = "test",
) -> dict:
    """
    Calcula todas las métricas predictivas requeridas por el model spec.

    Args:
        y_true:  etiquetas reales
        y_proba: probabilidades predichas P(home_win)
        label:   etiqueta para identificar el split en el reporte

    Returns:
        Diccionario con todas las métricas y si pasan los criterios de aceptación.
    """
    ll    = compute_log_loss(y_true, y_proba)
    bs    = compute_brier_score(y_true, y_proba)
    auc   = compute_roc_auc(y_true, y_proba)
    acc   = compute_accuracy(y_true, y_proba)
    ece   = compute_ece(y_true, y_proba)

    metrics = {
        "split": label,
        "n_samples": int(len(y_true)),
        "log_loss": round(ll, 4),
        "brier_score": round(bs, 4),
        "roc_auc": round(auc, 4),
        "accuracy": round(acc, 4),
        "ece": round(ece, 4),
        # Criterios de aceptación
        "passes_log_loss": ll < 0.68,
        "passes_brier": bs < 0.25,
        "passes_auc": auc > 0.55,
        "passes_ece": ece < 0.05,
    }
    metrics["passes_all"] = all([
        metrics["passes_log_loss"],
        metrics["passes_brier"],
        metrics["passes_auc"],
        metrics["passes_ece"],
    ])
    return metrics


def print_metrics_report(metrics: dict):
    """Imprime un reporte legible de las métricas."""
    print(f"\n{'='*55}")
    print(f"  Métricas — Split: {metrics['split'].upper()}  (n={metrics['n_samples']})")
    print(f"{'='*55}")

    checks = {
        "Log Loss   (< 0.68)": (metrics["log_loss"],   metrics["passes_log_loss"]),
        "Brier Score(< 0.25)": (metrics["brier_score"],metrics["passes_brier"]),
        "ROC-AUC    (> 0.55)": (metrics["roc_auc"],    metrics["passes_auc"]),
        "ECE        (< 0.05)": (metrics["ece"],         metrics["passes_ece"]),
    }
    for name, (value, passes) in checks.items():
        status = "[OK]" if passes else "[X]"
        print(f"  {status} {name}: {value:.4f}")

    print(f"  {'-'*51}")
    print(f"  Accuracy:                     {metrics['accuracy']:.4f}")
    overall = "[OK] PASA criterios" if metrics["passes_all"] else "[X] NO pasa todos los criterios"
    print(f"\n  Resultado: {overall}")
    print(f"{'='*55}\n")


# ---------------------------------------------------------------------------
# Métricas de regresión (margen y total)
# ---------------------------------------------------------------------------

def evaluate_regressor(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label: str = "test",
) -> dict:
    """
    Calcula métricas de regresión para margen o total de puntos.

    Criterios de aceptación:
      - Margen MAE < 10.0 puntos
      - Total MAE < 15.0 puntos

    Args:
        y_true: valores reales
        y_pred: valores predichos
        label:  etiqueta (ej: "margin", "total")

    Returns:
        Diccionario con MAE, RMSE, bias, correlación.
    """
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    bias = float(np.mean(y_pred - y_true))
    corr = float(np.corrcoef(y_true, y_pred)[0, 1]) if len(y_true) > 1 else 0.0

    return {
        "split": label,
        "n_samples": int(len(y_true)),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "bias": round(bias, 2),
        "correlation": round(corr, 4),
        "passes_mae_margin": mae < 10.0,
        "passes_mae_total": mae < 15.0,
    }


def print_regressor_report(metrics: dict, title: str = "Regresión"):
    """Imprime un reporte legible de métricas de regresión."""
    print(f"\n  --- {title} (n={metrics['n_samples']}) ---")
    print(f"  MAE:          {metrics['mae']:.2f} pts")
    print(f"  RMSE:         {metrics['rmse']:.2f} pts")
    print(f"  Bias:         {metrics['bias']:+.2f} pts")
    print(f"  Correlación:  {metrics['correlation']:.4f}")


# ---------------------------------------------------------------------------
# Métricas económicas (backtesting)
# ---------------------------------------------------------------------------

def compute_kelly_fraction(
    p: float, odds_decimal: float, fraction: float = 0.25
) -> float:
    """
    Kelly Criterion con fracción de seguridad.

    Calcula el tamaño óptimo de apuesta como proporción del bankroll.

    f* = (p × o - 1) / (o - 1)
    Apuesta = fraction × f*

    Args:
        p:             probabilidad estimada de ganar
        odds_decimal:  cuota decimal (ej: 1.85)
        fraction:      fracción de Kelly a usar (default 0.25 = quarter-Kelly)

    Returns:
        Fracción del bankroll a apostar. 0.0 si no hay edge.
    """
    edge = p * odds_decimal - 1.0
    if edge <= 0 or odds_decimal <= 1.0:
        return 0.0
    f_star = edge / (odds_decimal - 1.0)
    return max(0.0, fraction * f_star)


def compute_expected_value(p_home: float, odds_decimal: float) -> float:
    """
    Valor esperado de una apuesta al equipo local.

    EV = p × o - 1

    Args:
        p_home:        P(home_win) predicha por el modelo
        odds_decimal:  cuota decimal del mercado (ej: 1.85)

    Returns:
        EV como float. EV > 0 indica apuesta con ventaja.
    """
    return p_home * odds_decimal - 1.0


def compute_economic_metrics(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    odds: np.ndarray,
    ev_threshold: float = 0.05,
    confidence_threshold: float = 0.55,
    stake: float = 1.0,
) -> dict:
    """
    Simula apuestas usando la regla de decisión del model spec y calcula
    métricas económicas sobre el periodo de test.

    Regla de apuesta (model spec §5.2):
        Apostar solo si: EV > τ_EV (0.05) AND p > τ_confianza (0.55)

    Args:
        y_true:               resultados reales (1=local gana, 0=visitante)
        y_proba:              P(home_win) del modelo
        odds:                 cuotas decimales del mercado para home
        ev_threshold:         τ_EV mínimo para apostar (default 0.05)
        confidence_threshold: τ_confianza mínimo (default 0.55)
        stake:                unidades apostadas por partido

    Returns:
        Diccionario con ROI, win_rate, drawdown, n_bets, total_profit.
    """
    ev = y_proba * odds - 1.0
    bet_mask = (ev > ev_threshold) & (y_proba > confidence_threshold)

    n_bets = int(bet_mask.sum())
    if n_bets == 0:
        return {
            "n_bets": 0,
            "win_rate": None,
            "roi": None,
            "max_drawdown": None,
            "total_profit": 0.0,
            "total_staked": 0.0,
            "passes_roi": False,
            "passes_drawdown": False,
        }

    y_bet = y_true[bet_mask]
    odds_bet = odds[bet_mask]
    proba_bet = y_proba[bet_mask]

    # Ganancias por apuesta (stake fijo): si gana → (odds - 1) * stake; si pierde → -stake
    profits = np.where(y_bet == 1, (odds_bet - 1.0) * stake, -stake)
    cumulative = np.cumsum(profits)
    total_staked = n_bets * stake
    total_profit = float(profits.sum())
    roi = total_profit / total_staked

    # Win rate
    win_rate = float(y_bet.mean())

    # Drawdown máximo
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = running_max - cumulative
    max_drawdown = float(drawdowns.max())
    max_drawdown_pct = max_drawdown / total_staked if total_staked > 0 else 0.0

    # Kelly fraccional (quarter-Kelly)
    kelly_stakes = np.array([
        compute_kelly_fraction(p, o, fraction=0.25)
        for p, o in zip(proba_bet, odds_bet)
    ])
    kelly_profits = np.where(
        y_bet == 1, kelly_stakes * (odds_bet - 1.0), -kelly_stakes
    )
    kelly_total_staked = float(kelly_stakes.sum())
    kelly_total_profit = float(kelly_profits.sum())
    kelly_roi = (
        kelly_total_profit / kelly_total_staked
        if kelly_total_staked > 0 else 0.0
    )

    return {
        "n_bets": n_bets,
        "win_rate": round(win_rate, 4),
        "roi": round(roi, 4),
        "max_drawdown_units": round(max_drawdown, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "total_profit": round(total_profit, 4),
        "total_staked": round(total_staked, 4),
        "kelly_total_staked": round(kelly_total_staked, 4),
        "kelly_total_profit": round(kelly_total_profit, 4),
        "kelly_roi": round(kelly_roi, 4),
        "avg_kelly_stake": round(float(kelly_stakes.mean()), 4),
        # Criterios de aceptación (model spec §8.2)
        "passes_roi": roi > 0.0,
        "passes_drawdown": max_drawdown_pct < 0.30,
    }


def print_economic_report(eco: dict):
    """Imprime un reporte legible de las métricas económicas."""
    print(f"\n{'='*55}")
    print(f"  Backtesting Económico")
    print(f"{'='*55}")

    if eco["n_bets"] == 0:
        print("  Sin apuestas recomendadas en el periodo de test.")
        print(f"{'='*55}\n")
        return

    roi_status = "✅" if eco["passes_roi"] else "❌"
    dd_status  = "✅" if eco["passes_drawdown"] else "❌"

    print(f"  Apuestas realizadas:      {eco['n_bets']}")
    print(f"  Win Rate:                 {eco['win_rate']:.2%}")
    print(f"  {roi_status} ROI (> 0%):           {eco['roi']:.2%}")
    print(f"  {dd_status} Drawdown máx (< 30%): {eco['max_drawdown_pct']:.2%}")
    print(f"  Ganancia total:           {eco['total_profit']:+.2f} unidades")

    if eco.get("kelly_roi") is not None:
        print(f"  {'-'*51}")
        print(f"  Kelly fraccional (25%):")
        print(f"    Stake promedio:         {eco['avg_kelly_stake']:.4f}")
        print(f"    ROI Kelly:              {eco['kelly_roi']:.2%}")
        print(f"    Ganancia Kelly:         {eco['kelly_total_profit']:+.4f} unidades")

    print(f"{'='*55}\n")
