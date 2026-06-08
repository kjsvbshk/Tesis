"""
Deploy un modelo entrenado al Backend.

Pasos:
  1. Verifica que el .joblib existe en ML/models/
  2. Copia el .joblib al directorio de modelos del Backend (MODEL_DIR en .env)
  3. Registra la versión en sys.model_versions
  4. La activa opcionalmente (--activate)

Uso:
    python -m scripts.deploy_model --version v2.0.0
    python -m scripts.deploy_model --version v2.0.0 --activate
    python -m scripts.deploy_model --version v2.0.0 --activate --backend-dir ../Backend/ml/models
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.register_model_version import register_model_version, activate_version


ML_ROOT = Path(__file__).parent.parent
DEFAULT_BACKEND_MODEL_DIR = ML_ROOT.parent / "Backend" / "ml" / "models"


def _load_env_model_dir() -> Path | None:
    """Lee MODEL_DIR desde Backend/.env si existe."""
    env_path = ML_ROOT.parent / "Backend" / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("MODEL_DIR="):
            raw = line.split("=", 1)[1].strip()
            p = Path(raw)
            if not p.is_absolute():
                p = (ML_ROOT.parent / "Backend" / p).resolve()
            return p
    return None


def deploy_model(version: str, activate: bool, backend_dir: Path) -> None:
    src = ML_ROOT / "models" / f"nba_prediction_model_{version}.joblib"
    metadata_path = ML_ROOT / "models" / "metadata" / f"{version}_metadata.json"

    # 1. Verificar fuente
    if not src.exists():
        print(f"❌ No se encontró el modelo fuente: {src}")
        print(f"   Entrena primero con: python -m src.training.train --version {version}")
        sys.exit(1)

    # 2. Leer métricas para el resumen final
    metrics_summary = ""
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            meta = json.load(f)
        parts = []
        for key in ("log_loss", "roc_auc", "ece", "mae_margin", "mae_total"):
            if key in meta:
                parts.append(f"{key}={meta[key]}")
        metrics_summary = " | ".join(parts)

    # 3. Crear directorio destino si no existe
    backend_dir.mkdir(parents=True, exist_ok=True)
    dst = backend_dir / src.name

    if dst.exists():
        print(f"⚠️  ADVERTENCIA: {dst} ya existe — será sobreescrito.")

    # 4. Copiar
    shutil.copy2(src, dst)
    print(f"✅ Copiado: {src} → {dst}")

    # 5. Registrar en DB
    register_model_version(version=version, activate=activate)

    # 6. Resumen
    if activate:
        print(f"✅ Activado: {version}")
    else:
        print(f"ℹ️  Registrado sin activar. Para activar: python -m scripts.deploy_model --version {version} --activate")

    if metrics_summary:
        print(f"   {metrics_summary}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy un modelo ML entrenado al Backend")
    parser.add_argument("--version", required=True, help="Versión a deployar (ej: v2.0.0)")
    parser.add_argument("--activate", action="store_true", help="Activar la versión en Backend tras el deploy")
    parser.add_argument(
        "--backend-dir",
        default=None,
        help="Directorio destino de modelos en Backend (default: lee MODEL_DIR de Backend/.env)",
    )
    args = parser.parse_args()

    if args.backend_dir:
        target_dir = Path(args.backend_dir)
        if not target_dir.is_absolute():
            target_dir = (Path.cwd() / target_dir).resolve()
    else:
        target_dir = _load_env_model_dir() or DEFAULT_BACKEND_MODEL_DIR

    print(f"Directorio destino: {target_dir}")
    deploy_model(version=args.version, activate=args.activate, backend_dir=target_dir)
