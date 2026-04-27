"""
Pipeline principal de entrenamiento — NBA Prediction Model

Orquesta el flujo completo:
  1. Carga datos desde ml.ml_ready_games (Neon PostgreSQL)
  2. Construye la matriz de features en formato diferencial
  3. Aplica split temporal (train/test, sin validación aleatoria)
  4. Entrena RandomForest calibrado, XGBoost y Ensemble
  5. Evalúa todas las métricas del model spec
  6. Guarda el modelo en formato .joblib

Uso:
    python -m src.training.train
    python -m src.training.train --version v1.0.0 --model rf
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import joblib
from sqlalchemy import create_engine, text

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import db_config
from src.models.random_forest import NBARandomForest
from src.models.xgboost_model import NBAXGBoost
from src.models.poisson_model import NBABivariatePoisson
from src.models.ensemble import NBAEnsemble
from src.evaluation.metrics import evaluate_classifier, evaluate_regressor, compute_economic_metrics, print_metrics_report, print_regressor_report, print_economic_report
from src.evaluation.validation import temporal_train_test_split


# ---------------------------------------------------------------------------
# Configuración de features (model spec §6.2 — formato diferencial)
# ---------------------------------------------------------------------------

# Features primarias: diferencia entre equipo local y visitante
# NOTA: reb_diff/ast_diff/tov_diff EXCLUIDOS — son del partido actual (leakage).
#       Se usan las versiones rolling (shift(1) sobre partidos anteriores).
DIFF_FEATURES = [
    "ppg_diff",
    "net_rating_diff_rolling",
    "rest_days_diff",
    "injuries_diff",
    "pace_diff",
    "off_rating_diff",
    "def_rating_diff",
    "reb_rolling_diff",       # rolling last-5 (sin leakage)
    "ast_rolling_diff",       # rolling last-5 (sin leakage)
    "tov_rolling_diff",       # rolling last-5 (sin leakage)
    "win_rate_diff",          # tasa de victorias last-10 (sin leakage)
    # Nuevas features v2
    "efg_pct_diff",           # EFG% diferencial
    "tov_rate_diff",          # Turnover rate diferencial
    "oreb_pct_diff",          # Offensive rebound % diferencial
    "dreb_pct_diff",          # Defensive rebound % diferencial
    "elo_diff",               # Elo rating diferencial
    "streak_diff",            # Racha diferencial
    "home_away_split_diff",   # Home/Away win rate diferencial
]

# Features individuales que complementan (cuando el diferencial no es suficiente)
INDIVIDUAL_FEATURES = [
    "home_ppg_last5",
    "away_ppg_last5",
    "home_rest_days",
    "away_rest_days",
    "home_b2b",
    "away_b2b",
    "home_injuries_count",
    "away_injuries_count",
    "home_win_rate_last10",   # tasa de victorias individual (sin leakage)
    "away_win_rate_last10",
    # Nuevas features v2
    "home_elo",
    "away_elo",
    "home_streak",
    "away_streak",
    "h2h_home_advantage",
]

# Features de odds (baja cobertura ~1%, se excluyen por defecto)
ODDS_FEATURES = [
    "implied_prob_home",
    "implied_prob_away",
]

TARGET = "home_win"
TARGET_MARGIN = "point_diff"
DATE_COL = "fecha"


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def load_ml_ready_games() -> pd.DataFrame:
    """Carga la tabla ml.ml_ready_games desde Neon PostgreSQL."""
    database_url = db_config.get_database_url()
    ml_schema = db_config.get_schema("ml")
    engine = create_engine(database_url, pool_pre_ping=True, echo=False)

    print("Cargando ml.ml_ready_games desde Neon...")
    df = pd.read_sql(
        f"SELECT * FROM {ml_schema}.ml_ready_games ORDER BY {DATE_COL}",
        engine
    )
    print(f"  {len(df)} partidos cargados.")
    return df


def build_feature_matrix(df: pd.DataFrame, use_odds: bool = False) -> tuple:
    """
    Construye X (features) e y (target) desde el DataFrame.

    Selecciona features diferenciales + individuales.
    Filtra filas donde el target es NULL.

    Args:
        df:        DataFrame con ml_ready_games
        use_odds:  incluir features de odds (baja cobertura)

    Returns:
        (X, y, feature_cols, df_clean) donde df_clean conserva la fecha
        para el split temporal.
    """
    feature_cols = DIFF_FEATURES + INDIVIDUAL_FEATURES
    if use_odds:
        feature_cols += ODDS_FEATURES

    # Solo columnas que existen en el DataFrame
    feature_cols = [c for c in feature_cols if c in df.columns]

    # Filtrar filas sin target
    df_clean = df.dropna(subset=[TARGET]).copy()
    df_clean[TARGET] = df_clean[TARGET].astype(int)

    n_dropped = len(df) - len(df_clean)
    if n_dropped > 0:
        print(f"  Advertencia: {n_dropped} filas sin target eliminadas.")

    # Filtrar juegos con puntuación 0-0 (partidos futuros o sin datos reales de resultado)
    # El scraper guarda 0 en lugar de NULL cuando el partido no ha sido procesado aún.
    score_col_home = next((c for c in ['home_pts', 'home_score'] if c in df_clean.columns), None)
    score_col_away = next((c for c in ['away_pts', 'away_score'] if c in df_clean.columns), None)
    if score_col_home and score_col_away:
        zero_score = (
            (df_clean[score_col_home].fillna(0) == 0) &
            (df_clean[score_col_away].fillna(0) == 0)
        )
        n_zero = zero_score.sum()
        if n_zero > 0:
            print(f"  Advertencia: {n_zero} juegos con marcador 0-0 eliminados (sin datos reales).")
            df_clean = df_clean[~zero_score]

    X = df_clean[feature_cols].values
    y = df_clean[TARGET].values

    # Targets de regresión
    score_col_home = next((c for c in ['home_pts', 'home_score'] if c in df_clean.columns), None)
    score_col_away = next((c for c in ['away_pts', 'away_score'] if c in df_clean.columns), None)
    if score_col_home and score_col_away:
        home_pts = df_clean[score_col_home].fillna(0).values
        away_pts = df_clean[score_col_away].fillna(0).values
        df_clean['_total_points'] = home_pts + away_pts

    print(f"  Features: {len(feature_cols)}")
    print(f"  Muestras: {len(y)} (home_win={y.mean():.2%})")

    return X, y, feature_cols, df_clean


# ---------------------------------------------------------------------------
# Entrenamiento por tipo de modelo
# ---------------------------------------------------------------------------

def train_random_forest(X_train, y_train, feature_cols) -> NBARandomForest:
    print("\nEntrenando RandomForest (con calibración isotónica)...")
    model = NBARandomForest()
    model.fit(X_train, y_train, feature_names=feature_cols)
    print("  RandomForest entrenado.")
    return model


def train_xgboost(X_train, df_train) -> NBAXGBoost:
    print("\nEntrenando XGBoost (regresión de puntuaciones)...")
    y_home = df_train["home_score"].fillna(df_train["home_score"].median()).values
    y_away = df_train["away_score"].fillna(df_train["away_score"].median()).values
    model = NBAXGBoost()
    model.fit(X_train, y_home, y_away)
    print("  XGBoost entrenado.")
    return model


def train_poisson(X_train, df_train, feature_cols) -> NBABivariatePoisson:
    """
    Entrena el modelo Bivariate Poisson aislado (Karlis & Ntzoufras, 2003).

    Útil para benchmarking del Poisson contra el ensemble completo.
    """
    print("\nEntrenando Bivariate Poisson (Karlis & Ntzoufras, 2003)...")
    score_col_h = next((c for c in ['home_pts', 'home_score'] if c in df_train.columns), 'home_score')
    score_col_a = next((c for c in ['away_pts', 'away_score'] if c in df_train.columns), 'away_score')
    y_home = df_train[score_col_h].fillna(df_train[score_col_h].median()).values
    y_away = df_train[score_col_a].fillna(df_train[score_col_a].median()).values
    model = NBABivariatePoisson()
    model.fit(X_train, y_home, y_away, feature_names=feature_cols)
    print(f"  Bivariate Poisson entrenado (λ3 global = {model.lambda3_:.4f}).")
    return model


def train_ensemble(X_train, y_train, df_train, feature_cols) -> NBAEnsemble:
    print("\nEntrenando Ensemble (RF + XGBoost + Margin + Total)...")
    score_col_h = next((c for c in ['home_pts', 'home_score'] if c in df_train.columns), 'home_score')
    score_col_a = next((c for c in ['away_pts', 'away_score'] if c in df_train.columns), 'away_score')
    y_home = df_train[score_col_h].fillna(df_train[score_col_h].median()).values
    y_away = df_train[score_col_a].fillna(df_train[score_col_a].median()).values
    y_margin = (y_home - y_away).astype(float)
    y_total = (y_home + y_away).astype(float)
    model = NBAEnsemble()
    model.fit(X_train, y_train, y_home, y_away,
              y_margin=y_margin, y_total=y_total,
              feature_names=feature_cols)
    print("  Ensemble entrenado.")
    return model


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------

def print_calibration_curve(y_test, y_proba, n_bins=10):
    """Imprime la curva de calibración bin a bin para diagnóstico."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    print("\n  Curva de calibracion (predicted -> actual):")
    print(f"  {'Bin':<14} {'n':>5} {'Pred':>7} {'Actual':>8} {'Gap':>8}")
    print("  " + "-" * 44)
    for i in range(n_bins):
        mask = (y_proba >= bins[i]) & (y_proba < bins[i + 1])
        if mask.sum() == 0:
            continue
        pred_mean   = y_proba[mask].mean()
        actual_mean = y_test[mask].mean()
        gap = actual_mean - pred_mean
        print(f"  [{bins[i]:.1f}, {bins[i+1]:.1f})  {mask.sum():>5}   {pred_mean:.3f}   {actual_mean:.3f}   {gap:+.3f}")
    print()


def evaluate(model, X_test, y_test, df_test, model_name: str) -> dict:
    """Evalúa un modelo y retorna sus métricas completas."""
    print(f"\nEvaluando {model_name}...")

    # Obtener probabilidades
    if hasattr(model, "predict_home_win_proba"):
        y_proba = model.predict_home_win_proba(X_test)
    else:
        y_proba = model.predict_proba(X_test)[:, 1]

    pred_metrics = evaluate_classifier(y_test, y_proba, label="test")
    print_metrics_report(pred_metrics)
    print_calibration_curve(y_test, y_proba)

    # Métricas de regresión para margen y total (solo ensemble)
    reg_metrics = {}
    if hasattr(model, "predict_full"):
        score_col_h = next((c for c in ['home_pts', 'home_score'] if c in df_test.columns), None)
        score_col_a = next((c for c in ['away_pts', 'away_score'] if c in df_test.columns), None)
        if score_col_h and score_col_a:
            full = model.predict_full(X_test)
            y_margin_true = (df_test[score_col_h].values - df_test[score_col_a].values).astype(float)
            y_total_true = (df_test[score_col_h].values + df_test[score_col_a].values).astype(float)

            # Filtrar juegos con score 0-0
            valid = y_total_true > 0
            if valid.sum() > 0:
                margin_metrics = evaluate_regressor(y_margin_true[valid], full["predicted_margin"][valid], label="margin")
                total_metrics = evaluate_regressor(y_total_true[valid], full["predicted_total"][valid], label="total")
                print_regressor_report(margin_metrics, "Margen (home - away)")
                print_regressor_report(total_metrics, "Total puntos")
                reg_metrics = {"margin": margin_metrics, "total": total_metrics}

    # Métricas económicas si hay odds disponibles
    eco_metrics = {}
    if "implied_prob_home" in df_test.columns:
        import pandas as pd
        implied = pd.to_numeric(df_test["implied_prob_home"], errors="coerce").values
        valid_odds = ~np.isnan(implied) & (implied > 0)
        if valid_odds.sum() > 50:
            odds = np.where(valid_odds, 1.0 / np.where(valid_odds, implied, 1.0), np.nan)
            eco_metrics = compute_economic_metrics(
                y_test[valid_odds],
                y_proba[valid_odds],
                odds[valid_odds],
            )
            print_economic_report(eco_metrics)

    return {**pred_metrics, **eco_metrics, **reg_metrics}


# ---------------------------------------------------------------------------
# Guardado del modelo
# ---------------------------------------------------------------------------

def save_model(model, version: str, metrics: dict, model_name: str, feature_cols: list):
    """
    Guarda el modelo en .joblib y sus metadatos en JSON.

    Paths de salida:
      ML/models/nba_prediction_model_{version}.joblib
      ML/models/metadata/{version}_metadata.json
    """
    models_dir = Path(__file__).parent.parent.parent / "models"
    metadata_dir = models_dir / "metadata"
    models_dir.mkdir(exist_ok=True)
    metadata_dir.mkdir(exist_ok=True)

    model_path = models_dir / f"nba_prediction_model_{version}.joblib"
    metadata_path = metadata_dir / f"{version}_metadata.json"

    # Guardar modelo
    joblib.dump(model, model_path)
    print(f"\nModelo guardado: {model_path}")

    # Guardar metadatos
    metadata = {
        "version": version,
        "model_type": model_name,
        "feature_columns": feature_cols,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"Metadatos guardados: {metadata_path}")

    return str(model_path)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def train_model(version: str = "v1.0.0", model_type: str = "ensemble", use_odds: bool = False):
    """
    Ejecuta el pipeline completo de entrenamiento.

    Args:
        version:    versión del modelo (ej: "v1.0.0")
        model_type: "rf" | "xgb" | "ensemble"
        use_odds:   incluir features de odds (baja cobertura)

    Returns:
        (model, metrics, model_path)
    """
    print("=" * 60)
    print(f"NBA Prediction Model — Entrenamiento {version}")
    print(f"Tipo: {model_type.upper()}   Odds features: {use_odds}")
    print("=" * 60)

    # 1. Cargar datos
    df = load_ml_ready_games()

    # 2. Construir features
    print("\nConstruyendo matriz de features...")
    X, y, feature_cols, df_clean = build_feature_matrix(df, use_odds=use_odds)

    # 3. Split temporal
    print("\nAplicando split temporal (80/20)...")
    df_train, df_test = temporal_train_test_split(df_clean, date_col=DATE_COL, test_size=0.20)

    # Usar los DataFrames directamente (temporal_train_test_split hace reset_index internamente)
    X_train = df_train[feature_cols].values
    y_train = df_train[TARGET].values
    X_test  = df_test[feature_cols].values
    y_test  = df_test[TARGET].values

    # 4. Entrenar modelo
    if model_type == "rf":
        model = train_random_forest(X_train, y_train, feature_cols)
        model_name = "RandomForest"
    elif model_type == "xgb":
        model = train_xgboost(X_train, df_train)
        model_name = "XGBoost"
    elif model_type == "poisson":
        model = train_poisson(X_train, df_train, feature_cols)
        model_name = "BivariatePoisson"
    elif model_type == "ensemble":
        model = train_ensemble(X_train, y_train, df_train, feature_cols)
        model_name = "Ensemble (RF+XGB+Poisson)"
    else:
        raise ValueError(
            f"model_type debe ser 'rf', 'xgb', 'poisson' o 'ensemble'. "
            f"Recibido: {model_type}"
        )

    # 5. Evaluar
    metrics = evaluate(model, X_test, y_test, df_test, model_name)

    # 6. Guardar
    model_path = save_model(model, version, metrics, model_name, feature_cols)

    print("\n" + "=" * 60)
    print(f"Entrenamiento completado. Modelo: {model_path}")
    print("=" * 60)

    return model, metrics, model_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrenamiento del modelo NBA")
    parser.add_argument("--version",    default="v2.1.0",
                        help="Versión del modelo (ej: v2.1.0). Default v2.1.0 incluye Bivariate Poisson.")
    parser.add_argument("--model",      default="ensemble",
                        help="Tipo: rf | xgb | poisson | ensemble")
    parser.add_argument("--use-odds",   action="store_true", help="Incluir features de odds")
    args = parser.parse_args()

    train_model(
        version=args.version,
        model_type=args.model,
        use_odds=args.use_odds,
    )
