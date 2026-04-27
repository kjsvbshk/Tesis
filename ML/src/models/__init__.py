"""
Modelos de machine learning para predicción NBA.

  NBARandomForest      — clasificador binario calibrado (home_win)
  NBAXGBoost           — regresor de puntuaciones (home_score, away_score)
  NBABivariatePoisson  — modelo Karlis & Ntzoufras 2003 (v2.1.0)
  NBAMarginModel       — regresor dedicado de margen (point_diff)
  NBATotalModel        — regresor dedicado de total de puntos
  NBAEnsemble          — stacking RF + XGBoost + Poisson + meta-LogReg
"""

from .random_forest import NBARandomForest
from .xgboost_model import NBAXGBoost
from .poisson_model import NBABivariatePoisson
from .margin_model import NBAMarginModel
from .total_model import NBATotalModel
from .ensemble import NBAEnsemble

__all__ = [
    "NBARandomForest",
    "NBAXGBoost",
    "NBABivariatePoisson",
    "NBAMarginModel",
    "NBATotalModel",
    "NBAEnsemble",
]
