"""
Capa de inferencia robusta a versión del modelo.

El backend puede cargar joblibs de varias versiones del NBAEnsemble
(v1.x: meta-features 2D; v2.1.0: 3D; v2.1.2/v2.2.0: 4D). Esta capa
reconstruye las predicciones desde los componentes individuales del
ensemble (rf, xgb, poisson, meta_learner, calibrator) para evitar
depender de que el código actual de `predict_full()` sea compatible
con el pickle cargado.

La lógica replica `evaluate_active_model.predict_legacy()` del módulo ML
y se mantiene independiente para no acoplar el backend a internals del
módulo ML.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class InferenceError(Exception):
    """Error base del módulo de inferencia."""


class ModelNotLoadedError(InferenceError):
    """El servicio recibió la solicitud pero no tiene modelo cargado."""


class ModelDimensionMismatchError(InferenceError):
    """X no coincide con la dimensión que el modelo espera (21 vs 33)."""


# ---------------------------------------------------------------------------
# Detección de versión / dimensión
# ---------------------------------------------------------------------------

def detect_feature_set(ensemble) -> str:
    """Devuelve 'v1' (21 features) o 'v2' (33 features) inspeccionando el
    RF interno del ensemble cargado.

    Usa el SimpleImputer del pipeline del RF para leer `n_features_in_`,
    que sklearn fija al hacer `fit`. Funciona para cualquier versión
    cargada desde joblib.
    """
    try:
        n = ensemble.rf.pipeline.named_steps["imputer"].n_features_in_
    except Exception as e:
        raise InferenceError(f"No se pudo inferir feature_set del modelo: {e}")
    if n == 21:
        return "v1"
    if n == 33:
        return "v2"
    if n == 35:
        return "v2_odds"
    if n == 47:
        return "v3"
    if n == 49:
        return "v3_odds"
    raise InferenceError(
        f"El RF interno espera {n} features, no es 21/33/35/47/49 (v1/v2/v2_odds/v3/v3_odds)"
    )


def detect_meta_dim(meta_learner) -> int:
    """Devuelve la dimensión esperada por el meta-learner (2, 3 o 4)."""
    # v2.1.2/v2.2.0: Pipeline(StandardScaler → LogReg)
    if hasattr(meta_learner, "named_steps"):
        for step in meta_learner.named_steps.values():
            if hasattr(step, "coef_"):
                return int(step.coef_.shape[1])
    # v1.x / v2.1.0: LogReg directo
    if hasattr(meta_learner, "coef_"):
        return int(meta_learner.coef_.shape[1])
    raise InferenceError("No se pudo inferir la dimensión del meta-learner")


# ---------------------------------------------------------------------------
# Predicción principal — reconstrucción desde componentes
# ---------------------------------------------------------------------------

def predict_home_win_proba(ensemble, X: np.ndarray) -> np.ndarray:
    """Reproduce `predict_home_win_proba` operando con los componentes del
    ensemble cargado. Funciona con joblibs v1.x, v2.1.0, v2.1.2 y v2.2.0
    sin depender de si el código actual de NBAEnsemble es compatible con
    el pickle.

    Args:
        ensemble: instancia cargada desde joblib.
        X:        array (n_samples, n_features) con features ya alineadas
                  al feature_set del modelo.

    Returns:
        array (n_samples,) con P(home_win) calibrada (isotónica aplicada
        si el modelo la tiene).
    """
    rf_proba = ensemble.rf.predict_home_win_proba(X)
    score_diff = ensemble.xgb.predict_score_diff(X)
    expected_dim = detect_meta_dim(ensemble.meta_learner)

    cols = [rf_proba.reshape(-1, 1), score_diff.reshape(-1, 1)]

    if expected_dim == 2:
        # v1.x — sólo RF + XGBoost
        pass
    elif expected_dim == 3:
        # v2.1.0 — añade poisson_proba
        if not hasattr(ensemble, "poisson") or ensemble.poisson is None:
            raise InferenceError("meta espera 3 cols pero el modelo no tiene poisson")
        cols.append(ensemble.poisson.predict_home_win_proba(X).reshape(-1, 1))
    elif expected_dim == 4:
        # v2.1.2 / v2.2.0 — features estructurales del poisson
        if not hasattr(ensemble, "poisson") or ensemble.poisson is None:
            raise InferenceError("meta espera 4 cols pero el modelo no tiene poisson")
        lam = ensemble.poisson.predict_lambdas(X)
        mu_diff = (lam["lambda1"] - lam["lambda2"]).reshape(-1, 1)
        sigma_diff = np.sqrt(
            np.clip(lam["lambda1"] + lam["lambda2"], 1e-9, None)
        ).reshape(-1, 1)
        cols.append(mu_diff)
        cols.append(sigma_diff)
    else:
        raise InferenceError(f"Dimensión de meta-learner inesperada: {expected_dim}")

    meta_X = np.hstack(cols)
    raw = ensemble.meta_learner.predict_proba(meta_X)[:, 1]

    calibrator = getattr(ensemble, "calibrator", None)
    if calibrator is not None:
        proba = calibrator.predict(raw)
        proba = np.clip(proba, 1e-6, 1.0 - 1e-6)
    else:
        proba = raw
    return proba


# ---------------------------------------------------------------------------
# Salida enriquecida (margin, total, team-props, poisson)
# ---------------------------------------------------------------------------

def predict_full_robust(ensemble, X: np.ndarray) -> Dict[str, Any]:
    """Versión robusta de `NBAEnsemble.predict_full()` que funciona con
    cualquier joblib (v1.x → v2.2.0). Devuelve un dict con tantas claves
    como salidas pueda producir el modelo cargado.

    Claves garantizadas:
      - home_win_probability, away_win_probability (calibradas)

    Claves opcionales (presentes si el modelo las soporta):
      - predicted_home_score, predicted_away_score, score_diff
      - predicted_margin, predicted_total
      - rf_probability
      - poisson_probability, poisson_lambda1/2/3, poisson_home_score, poisson_away_score
      - team_props: {home: {...}, away: {...}, labels: {...}}
    """
    out: Dict[str, Any] = {}

    # Probabilidad de victoria local (siempre)
    home_proba = predict_home_win_proba(ensemble, X)
    out["home_win_probability"] = home_proba
    out["away_win_probability"] = 1.0 - home_proba

    # Señal del RF (siempre — el RF está en todas las versiones)
    out["rf_probability"] = ensemble.rf.predict_home_win_proba(X)

    # XGBoost: scores y diff
    try:
        h_score, a_score = ensemble.xgb.predict_scores(X)
        out["predicted_home_score"] = h_score
        out["predicted_away_score"] = a_score
        out["score_diff"] = h_score - a_score
    except Exception:
        pass

    # Margen y total dedicados (v2.x)
    if hasattr(ensemble, "margin_model") and getattr(ensemble.margin_model, "is_fitted", False):
        out["predicted_margin"] = ensemble.margin_model.predict_margin(X)
    if hasattr(ensemble, "total_model") and getattr(ensemble.total_model, "is_fitted", False):
        out["predicted_total"] = ensemble.total_model.predict_total(X)

    # Poisson (v2.1.x +)
    poisson = getattr(ensemble, "poisson", None)
    if poisson is not None and getattr(poisson, "is_fitted", False):
        out["poisson_probability"] = poisson.predict_home_win_proba(X)
        lam = poisson.predict_lambdas(X)
        out["poisson_lambda1"] = lam["lambda1"]
        out["poisson_lambda2"] = lam["lambda2"]
        out["poisson_lambda3"] = lam["lambda3"]
        out["poisson_home_score"] = lam["mu_home"]
        out["poisson_away_score"] = lam["mu_away"]

    # Team-props (v2.2.0+)
    team_stat_models = getattr(ensemble, "team_stat_models", None)
    if team_stat_models:
        team_props = {"home": {}, "away": {}, "labels": {}}
        labels_map = {
            "reb": "Rebotes totales",
            "ast": "Asistencias",
            "stl": "Robos",
            "blk": "Bloqueos",
            "to":  "Turnovers (pérdidas)",
        }
        for key, model in team_stat_models.items():
            if not getattr(model, "is_fitted", False):
                continue
            try:
                side, kind = key.split("_", 1)
            except ValueError:
                continue
            if side not in ("home", "away"):
                continue
            team_props[side][kind] = model.predict(X)
            team_props["labels"][kind] = labels_map.get(kind, kind)
        if team_props["home"] or team_props["away"]:
            out["team_props"] = team_props

    return out


# ---------------------------------------------------------------------------
# Helpers de validación y serialización
# ---------------------------------------------------------------------------

def _to_scalar(value: Any) -> Optional[float]:
    """Convierte arrays (1,) o (n,) a float escalar tomando el primer elemento.
    Devuelve None si el valor es NaN o el array está vacío."""
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        value = float(value.ravel()[0])
    else:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
    if np.isnan(value):
        return None
    return value


def extract_single_sample(full_output: Dict[str, Any], idx: int = 0) -> Dict[str, Any]:
    """Convierte el dict de arrays de predict_full_robust en un dict escalar
    para una sola muestra (la primera por defecto), apto para serializar
    a JSON y mapear al schema PredictionResponse.

    Maneja team_props recursivamente.
    """
    scalar: Dict[str, Any] = {}
    for k, v in full_output.items():
        if k == "team_props" and isinstance(v, dict):
            scalar["team_props"] = {
                "home": {kind: _to_scalar(arr[idx] if hasattr(arr, "__getitem__") else arr)
                         for kind, arr in v.get("home", {}).items()},
                "away": {kind: _to_scalar(arr[idx] if hasattr(arr, "__getitem__") else arr)
                         for kind, arr in v.get("away", {}).items()},
                "labels": v.get("labels", {}),
            }
        elif isinstance(v, np.ndarray) and v.size > idx:
            scalar[k] = _to_scalar(v[idx])
        else:
            scalar[k] = _to_scalar(v)
    return scalar


def validate_prediction(scalar: Dict[str, Any]) -> None:
    """Valida que la predicción está en rangos sanos. Lanza InferenceError
    si la salida es inválida.

    Validaciones:
      - home_win_probability ∈ [0, 1]
      - scores ∈ [50, 200] (rango muy amplio para no ser demasiado estricto)
      - probabilidades complementarias suman ≈ 1
    """
    p_h = scalar.get("home_win_probability")
    p_a = scalar.get("away_win_probability")
    if p_h is None or p_a is None:
        raise InferenceError("Predicción inválida: probabilidades faltantes o NaN")
    if not (0.0 <= p_h <= 1.0):
        raise InferenceError(f"P(home_win) fuera de rango: {p_h}")
    if abs((p_h + p_a) - 1.0) > 1e-3:
        raise InferenceError(f"P(home) + P(away) != 1: {p_h} + {p_a}")

    for key in ("predicted_home_score", "predicted_away_score"):
        v = scalar.get(key)
        if v is not None and not (50.0 <= v <= 200.0):
            raise InferenceError(f"{key} fuera de rango realista NBA: {v}")
