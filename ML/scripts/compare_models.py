"""
Compara métricas entre versiones de modelos registradas.

Lee los archivos de metadatos de cada versión y muestra una tabla
comparativa con todas las métricas del model spec.

Uso:
    python scripts/compare_models.py
    python scripts/compare_models.py --versions v1.0.0 v1.1.0
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


METRIC_CRITERIA = {
    "log_loss":    ("<", 0.68),
    "brier_score": ("<", 0.25),
    "roc_auc":     (">", 0.55),
    "ece":         ("<", 0.05),
}


def load_metadata(version: str) -> dict:
    ml_root = Path(__file__).parent.parent
    meta_path = ml_root / "models" / "metadata" / f"{version}_metadata.json"
    if not meta_path.exists():
        return None
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


def passes_criterion(metric: str, value: float) -> bool:
    if metric not in METRIC_CRITERIA:
        return True
    op, threshold = METRIC_CRITERIA[metric]
    if op == "<":
        return value < threshold
    return value > threshold


def compare_models(versions: list = None):
    """
    Compara versiones de modelos según sus metadatos.

    Si no se especifican versiones, lee todos los JSON en models/metadata/.
    """
    ml_root = Path(__file__).parent.parent
    metadata_dir = ml_root / "models" / "metadata"

    if not versions:
        # Leer todos los metadatos disponibles
        versions = [p.stem.replace("_metadata", "") for p in metadata_dir.glob("*_metadata.json")]
        versions.sort()

    if not versions:
        print("No hay modelos entrenados. Ejecutar primero: python -m src.training.train")
        return

    print(f"\n{'='*70}")
    print(f"  Comparación de Modelos — {len(versions)} versión(es)")
    print(f"{'='*70}")

    all_data = []
    for v in versions:
        meta = load_metadata(v)
        if meta is None:
            print(f"  Advertencia: no se encontraron metadatos para {v}")
            continue
        all_data.append((v, meta))

    if not all_data:
        print("No se encontraron metadatos.")
        return

    # Tabla de métricas predictivas
    print(f"\n{'Versión':<12} {'Tipo':<20} {'LogLoss':<10} {'Brier':<10} {'AUC':<10} {'ECE':<10} {'Estado'}")
    print("-" * 90)

    for v, meta in all_data:
        m = meta.get("metrics", {})
        model_type = meta.get("model_type", "?")[:18]

        ll  = m.get("log_loss",    "N/A")
        bs  = m.get("brier_score", "N/A")
        auc = m.get("roc_auc",     "N/A")
        ece = m.get("ece",         "N/A")

        def fmt(val, metric):
            if val == "N/A":
                return f"{'N/A':<9}"
            ok = passes_criterion(metric, val)
            flag = "✅" if ok else "❌"
            return f"{flag}{val:.4f}  "

        passes = m.get("passes_all", False)
        status = "✅ PASA" if passes else "❌ FALLA"

        print(
            f"{v:<12} {model_type:<20} "
            f"{fmt(ll, 'log_loss')}"
            f"{fmt(bs, 'brier_score')}"
            f"{fmt(auc, 'roc_auc')}"
            f"{fmt(ece, 'ece')}"
            f"{status}"
        )

    # Criterios de aceptación (referencia)
    print(f"\n  Criterios: LogLoss < 0.68 | Brier < 0.25 | AUC > 0.55 | ECE < 0.05")

    # Métricas económicas si están disponibles
    eco_versions = [(v, meta) for v, meta in all_data if "roi" in meta.get("metrics", {})]
    if eco_versions:
        print(f"\n{'─'*70}")
        print(f"  Métricas económicas (backtesting)")
        print(f"{'─'*70}")
        print(f"\n{'Versión':<12} {'N Apuestas':<12} {'Win Rate':<12} {'ROI':<12} {'Drawdown':<12} {'Estado'}")
        print("-" * 70)

        for v, meta in eco_versions:
            m = meta.get("metrics", {})
            n_bets  = m.get("n_bets", 0)
            wr      = m.get("win_rate", None)
            roi     = m.get("roi", None)
            dd      = m.get("max_drawdown_pct", None)
            passes_roi = m.get("passes_roi", False)
            passes_dd  = m.get("passes_drawdown", False)

            roi_str = f"{'✅' if passes_roi else '❌'}{roi:.2%}" if roi is not None else "N/A"
            dd_str  = f"{'✅' if passes_dd else '❌'}{dd:.2%}" if dd is not None else "N/A"
            wr_str  = f"{wr:.2%}" if wr is not None else "N/A"

            print(f"{v:<12} {n_bets:<12} {wr_str:<12} {roi_str:<13} {dd_str}")

    # Recomendación de mejor modelo
    passed = [(v, meta) for v, meta in all_data if meta.get("metrics", {}).get("passes_all", False)]
    if passed:
        best = min(passed, key=lambda x: x[1].get("metrics", {}).get("log_loss", 999))
        print(f"\n  Mejor modelo: {best[0]} (menor Log Loss entre los que pasan criterios)")
    else:
        print(f"\n  Ningún modelo pasa todos los criterios de aceptación aún.")

    print(f"{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comparar versiones de modelos")
    parser.add_argument("--versions", nargs="+", default=None, help="Versiones a comparar (ej: v1.0.0 v1.1.0)")
    args = parser.parse_args()

    compare_models(args.versions)
