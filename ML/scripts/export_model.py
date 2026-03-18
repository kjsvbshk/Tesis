"""
Exporta un modelo entrenado al directorio del Backend.

Copia el .joblib desde ML/models/ a Backend/ml/models/ para que
el servicio de predicciones del Backend pueda cargarlo.

Uso:
    python scripts/export_model.py --version v1.0.0
    python scripts/export_model.py --version v1.0.0 --set-default
"""

import argparse
import shutil
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def export_model(version: str, set_default: bool = False):
    """
    Copia el modelo .joblib y sus metadatos al directorio del Backend.

    Args:
        version:     versión a exportar (ej: "v1.0.0")
        set_default: si True, crea además una copia sin versión como
                     nba_prediction_model.joblib (fallback del Backend)
    """
    ml_root     = Path(__file__).parent.parent
    backend_dir = ml_root.parent / "Backend" / "ml" / "models"
    backend_dir.mkdir(parents=True, exist_ok=True)

    # Archivo fuente
    src_model = ml_root / "models" / f"nba_prediction_model_{version}.joblib"
    src_meta  = ml_root / "models" / "metadata" / f"{version}_metadata.json"

    if not src_model.exists():
        print(f"Error: no se encontró el modelo {src_model}")
        print("Ejecutar primero: python -m src.training.train --version {version}")
        sys.exit(1)

    # Destino
    dst_model = backend_dir / f"nba_prediction_model_{version}.joblib"
    shutil.copy2(src_model, dst_model)
    print(f"Modelo exportado: {dst_model}")

    if src_meta.exists():
        dst_meta = backend_dir / f"{version}_metadata.json"
        shutil.copy2(src_meta, dst_meta)
        print(f"Metadatos exportados: {dst_meta}")

        # Mostrar métricas del modelo exportado
        with open(src_meta, encoding="utf-8") as f:
            meta = json.load(f)
        m = meta.get("metrics", {})
        print(f"\nMétricas del modelo exportado:")
        for key in ["log_loss", "brier_score", "roc_auc", "ece"]:
            if key in m:
                print(f"  {key}: {m[key]}")
        if "passes_all" in m:
            status = "✅ Pasa todos los criterios" if m["passes_all"] else "❌ No pasa todos los criterios"
            print(f"  {status}")

    # Copia como fallback sin versión
    if set_default:
        dst_default = backend_dir / "nba_prediction_model.joblib"
        shutil.copy2(src_model, dst_default)
        print(f"\nCopia default creada: {dst_default}")

    print("\nExportación completada.")
    print("Siguiente paso: ejecutar scripts/register_model_version.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exportar modelo al Backend")
    parser.add_argument("--version",     required=True, help="Versión del modelo (ej: v1.0.0)")
    parser.add_argument("--set-default", action="store_true", help="Crear copia sin versión como fallback")
    args = parser.parse_args()

    export_model(args.version, args.set_default)
