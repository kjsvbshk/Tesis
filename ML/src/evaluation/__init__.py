"""
Evaluación y validación de modelos NBA.

  metrics    — Log Loss, Brier Score, ROC-AUC, ECE, métricas económicas
  validation — split temporal, expanding window CV
"""

from .metrics import (
    evaluate_classifier,
    compute_economic_metrics,
    print_metrics_report,
    print_economic_report,
)
from .validation import temporal_train_test_split, expanding_window_splits

__all__ = [
    "evaluate_classifier",
    "compute_economic_metrics",
    "print_metrics_report",
    "print_economic_report",
    "temporal_train_test_split",
    "expanding_window_splits",
]
