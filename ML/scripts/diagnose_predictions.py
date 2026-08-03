"""
Diagnóstico de efectividad del modelo activo — dos modos.

MODO 1 (por partido):  explica por qué el modelo predijo lo que predijo.
    Muestra equipos, resultado real, P(home_win), marcador predicho por la
    cabeza XGBoost, y cuántas features llegaron degeneradas (nulas o = mediana),
    que es la causa habitual de predicciones "a ciegas" al inicio de temporada.

MODO 2 (agregado):  mide la ACCURACY REAL de acierto de ganador sobre un rango
    de fechas, para contrastar con el 63-66% publicado. Distingue el ganador
    según P(home_win) (la cabeza correcta) del ganador según el marcador XGBoost.

Necesita Neon + el .joblib activo.

Uso:
    cd ML
    python -m scripts.diagnose_predictions --game 401859965 --game 401859967
    python -m scripts.diagnose_predictions --desde 2025-10-01 --hasta 2026-03-29
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import joblib

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.train import load_ml_ready_games, build_feature_matrix, TARGET, DATE_COL

ML_ROOT = Path(__file__).parent.parent


def _load_active(version):
    p = ML_ROOT / "models" / f"nba_prediction_model_{version}.joblib"
    if not p.exists():
        print(f"ERROR: no se encontró {p}")
        sys.exit(1)
    return joblib.load(p)


def _predict(model, X):
    try:
        proba = model.predict_home_win_proba(X)
    except Exception:
        from scripts.evaluate_active_model import predict_legacy
        proba = predict_legacy(model, X)
    scores = None
    try:
        h, a = model.xgb.predict_scores(X)
        scores = list(zip(np.asarray(h), np.asarray(a)))
    except Exception:
        pass
    return np.asarray(proba), scores


def modo_partido(model, df, feature_cols, game_ids):
    # medianas de entrenamiento para detectar features degeneradas
    med = np.nanmedian(df[feature_cols].astype(float).values, axis=0)
    for gid in game_ids:
        row = df[df["game_id"] == int(gid)]
        if row.empty:
            print(f"\n[{gid}] no está en ml.ml_ready_games")
            continue
        r = row.iloc[0]
        X = row[feature_cols].astype(float).values
        proba, scores = _predict(model, X)
        p = float(proba[0])
        hs, as_ = (r.get("home_score"), r.get("away_score"))
        real = None
        if hs is not None and as_ is not None and (hs or as_):
            real = "LOCAL" if hs > as_ else "VISITANTE"
        pred = "LOCAL" if p >= 0.5 else "VISITANTE"
        # features degeneradas
        vals = X[0]
        n_nan = int(np.isnan(vals).sum())
        n_med = int(np.sum(np.isclose(np.nan_to_num(vals), med, rtol=1e-3, atol=1e-6)))
        print(f"\n══ Partido {gid} ══  {r['home_team']} (local) vs {r['away_team']} (visitante)  ·  {r['fecha']}")
        print(f"   P(gana local) = {p:.3f}  →  predice: {pred}")
        if scores:
            print(f"   Marcador XGBoost: local {scores[0][0]:.0f} - visitante {scores[0][1]:.0f}")
        if real:
            print(f"   Resultado REAL: {int(hs)}-{int(as_)}  →  ganó: {real}   {'✓ ACIERTO' if pred==real else '✗ FALLO'}")
        else:
            print("   Resultado REAL: sin marcador (partido futuro/no jugado)")
        print(f"   Features degeneradas: {n_nan}/{len(vals)} nulas · {n_med}/{len(vals)} iguales a la mediana "
              f"→ {'ALERTA: predicción con poca información' if (n_nan+n_med) > len(vals)*0.4 else 'cobertura aceptable'}")


def modo_agregado(model, df, feature_cols, desde, hasta):
    d = df.copy()
    d = d[d[TARGET].notna()]
    d = d[(d["home_score"].fillna(0) > 0) | (d["away_score"].fillna(0) > 0)]
    d[DATE_COL] = d[DATE_COL].astype(str)
    if desde: d = d[d[DATE_COL] >= desde]
    if hasta: d = d[d[DATE_COL] <= hasta]
    if d.empty:
        print("No hay partidos jugados en ese rango.")
        return
    X = d[feature_cols].astype(float).values
    proba, scores = _predict(model, X)
    y = d[TARGET].astype(int).values
    pred_win = (proba >= 0.5).astype(int)
    acc = float((pred_win == y).mean())
    base = float(max(y.mean(), 1 - y.mean()))  # siempre-mayoría
    print(f"\n══ ACCURACY DE ACIERTO DE GANADOR ══  ({desde or 'inicio'} → {hasta or 'fin'})")
    print(f"   Partidos jugados evaluados: {len(y)}")
    print(f"   Aciertos del modelo (P home_win): {acc*100:.1f} %")
    print(f"   Línea base (siempre el mayoritario): {base*100:.1f} %")
    print(f"   Tasa de victorias locales en el rango: {y.mean()*100:.1f} %")
    if scores:
        # acierto según la cabeza de marcador (para ver la discrepancia)
        sc = np.array([1 if h > a else 0 for h, a in scores])
        print(f"   [ref] Aciertos si se usara el MARCADOR XGBoost: {(sc==y).mean()*100:.1f} % "
              f"(discrepa con la cabeza de probabilidad en {(sc!=pred_win).mean()*100:.0f}% de los partidos)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v3.1.0")
    ap.add_argument("--game", action="append", default=[], help="game_id a diagnosticar (repetible)")
    ap.add_argument("--desde", default=None, help="fecha inicio YYYY-MM-DD (modo agregado)")
    ap.add_argument("--hasta", default=None, help="fecha fin YYYY-MM-DD (modo agregado)")
    args = ap.parse_args()

    model = _load_active(args.version)
    df = load_ml_ready_games()
    _, _, feature_cols, df_clean = build_feature_matrix(df)  # 52 features, defaults v3.1.0
    # usar df completo (no solo limpio) para poder localizar cualquier game_id
    df_all = df.copy()
    for c in feature_cols:
        if c not in df_all.columns:
            df_all[c] = np.nan

    if args.game:
        modo_partido(model, df_all, feature_cols, args.game)
    if args.desde or args.hasta or not args.game:
        modo_agregado(model, df_clean, feature_cols, args.desde, args.hasta)


if __name__ == "__main__":
    main()
