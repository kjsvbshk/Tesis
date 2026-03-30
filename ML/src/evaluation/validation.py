"""
Estrategia de validación temporal para modelos NBA.

El model spec prohíbe explícitamente la validación aleatoria (train_test_split).
Todos los splits deben ser temporales para respetar la naturaleza secuencial
de los datos deportivos y evitar data leakage.

Implementa:
  - Split temporal simple (80/20 por fecha)
  - Expanding window cross-validation (ventana expansiva)
  - Backtesting integrado con métricas económicas
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Generator


# ---------------------------------------------------------------------------
# Split temporal simple
# ---------------------------------------------------------------------------

def temporal_train_test_split(
    df: pd.DataFrame,
    date_col: str = "fecha",
    test_size: float = 0.20,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Divide el dataset en train y test usando un corte temporal.

    El test set contiene los partidos MÁS RECIENTES (últimos `test_size`%).
    No hay datos del futuro en el set de entrenamiento.

    Args:
        df:        DataFrame con columna de fecha
        date_col:  nombre de la columna de fecha
        test_size: fracción del dataset para test (default 0.20 = 20%)

    Returns:
        (df_train, df_test)
    """
    df_sorted = df.sort_values(date_col).reset_index(drop=True)
    n = len(df_sorted)
    split_idx = int(n * (1 - test_size))

    df_train = df_sorted.iloc[:split_idx].copy()
    df_test  = df_sorted.iloc[split_idx:].copy()

    cutoff_date = df_sorted[date_col].iloc[split_idx]
    print(f"Split temporal:")
    print(f"  Train: {len(df_train)} partidos ({df_sorted[date_col].iloc[0]} -> {df_sorted[date_col].iloc[split_idx-1]})")
    print(f"  Test:  {len(df_test)} partidos  ({cutoff_date} -> {df_sorted[date_col].iloc[-1]})")

    return df_train, df_test


# ---------------------------------------------------------------------------
# Expanding Window Cross-Validation
# ---------------------------------------------------------------------------

def expanding_window_splits(
    df: pd.DataFrame,
    date_col: str = "fecha",
    n_splits: int = 5,
    min_train_size: float = 0.40,
) -> Generator[Tuple[pd.Index, pd.Index], None, None]:
    """
    Genera índices para validación cruzada con ventana expansiva.

    Esquema con n_splits=5 y min_train_size=0.40:

        Split 1: Train [  0% → 40%]  Val [40% → 52%]
        Split 2: Train [  0% → 52%]  Val [52% → 64%]
        Split 3: Train [  0% → 64%]  Val [64% → 76%]
        Split 4: Train [  0% → 76%]  Val [76% → 88%]
        Split 5: Train [  0% → 88%]  Val [88% → 100%]

    El conjunto de entrenamiento siempre empieza desde el principio y
    se EXPANDE en cada fold. El conjunto de validación siempre es posterior
    al de entrenamiento.

    Args:
        df:             DataFrame ordenado por fecha
        date_col:       columna de fecha
        n_splits:       número de folds
        min_train_size: fracción mínima del dataset para primer fold de train

    Yields:
        (train_indices, val_indices) como pd.Index
    """
    df_sorted = df.sort_values(date_col).reset_index(drop=True)
    n = len(df_sorted)

    # Dividir la parte post-min_train en n_splits segmentos iguales
    start_val = int(n * min_train_size)
    step = (n - start_val) // n_splits

    for i in range(n_splits):
        val_start = start_val + i * step
        val_end   = val_start + step if i < n_splits - 1 else n

        train_idx = df_sorted.index[:val_start]
        val_idx   = df_sorted.index[val_start:val_end]

        yield train_idx, val_idx


def cross_validate_temporal(
    model_class,
    df: pd.DataFrame,
    feature_cols: list,
    target_col: str = "home_win",
    date_col: str = "fecha",
    n_splits: int = 5,
    model_params: dict = None,
) -> List[dict]:
    """
    Ejecuta validación cruzada temporal con expanding window.

    En cada fold:
    1. Instancia un modelo nuevo
    2. Entrena en el set de entrenamiento del fold
    3. Evalúa en el set de validación del fold
    4. Registra métricas

    Args:
        model_class:  clase del modelo (NBARandomForest, NBAEnsemble, etc.)
        df:           DataFrame con features y target
        feature_cols: columnas a usar como features
        target_col:   nombre del target
        date_col:     columna de fecha
        n_splits:     número de folds
        model_params: parámetros opcionales para el modelo

    Returns:
        Lista de diccionarios con métricas por fold.
    """
    from src.evaluation.metrics import evaluate_classifier

    results = []
    df_sorted = df.sort_values(date_col).reset_index(drop=True)

    for fold_idx, (train_idx, val_idx) in enumerate(
        expanding_window_splits(df_sorted, date_col, n_splits), start=1
    ):
        df_train = df_sorted.loc[train_idx]
        df_val   = df_sorted.loc[val_idx]

        X_train = df_train[feature_cols].values
        y_train = df_train[target_col].astype(int).values
        X_val   = df_val[feature_cols].values
        y_val   = df_val[target_col].astype(int).values

        model = model_class(**(model_params or {})) if model_params else model_class()
        model.fit(X_train, y_train, feature_names=feature_cols)

        y_proba = model.predict_home_win_proba(X_val)
        fold_metrics = evaluate_classifier(y_val, y_proba, label=f"fold_{fold_idx}")
        fold_metrics["train_size"] = len(df_train)
        fold_metrics["val_size"]   = len(df_val)

        results.append(fold_metrics)

        print(f"  Fold {fold_idx}: "
              f"LogLoss={fold_metrics['log_loss']:.4f}  "
              f"AUC={fold_metrics['roc_auc']:.4f}  "
              f"Brier={fold_metrics['brier_score']:.4f}  "
              f"ECE={fold_metrics['ece']:.4f}")

    return results


def summarize_cv_results(cv_results: List[dict]) -> dict:
    """Calcula media y desviación estándar de las métricas de CV."""
    metric_keys = ["log_loss", "brier_score", "roc_auc", "accuracy", "ece"]
    summary = {}
    for key in metric_keys:
        values = [r[key] for r in cv_results]
        summary[f"{key}_mean"] = round(np.mean(values), 4)
        summary[f"{key}_std"]  = round(np.std(values), 4)
    return summary
