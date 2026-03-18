"""
Registra un modelo entrenado en la tabla sys.model_versions del Backend.

Permite al Backend saber qué modelo cargar mediante la columna is_active.
Solo puede haber una versión activa al mismo tiempo.

Uso:
    python scripts/register_model_version.py --version v1.0.0
    python scripts/register_model_version.py --version v1.0.0 --activate
    python scripts/register_model_version.py --activate-only v1.0.0
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config


def register_model_version(
    version: str,
    activate: bool = False,
    description: str = None,
):
    """
    Inserta o actualiza un registro en sys.model_versions.

    Si activate=True, desactiva todas las versiones anteriores y activa la nueva.

    Args:
        version:     versión a registrar (ej: "v1.0.0")
        activate:    si True, marca esta versión como activa
        description: descripción opcional del modelo
    """
    ml_root = Path(__file__).parent.parent
    metadata_path = ml_root / "models" / "metadata" / f"{version}_metadata.json"

    # Leer metadatos si existen
    metadata_json = {}
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            metadata_json = json.load(f)
        print(f"Metadatos leídos desde: {metadata_path}")
    else:
        print(f"Advertencia: no se encontraron metadatos en {metadata_path}")

    # Descripción por defecto
    if not description:
        model_type = metadata_json.get("model_type", "Ensemble")
        description = f"NBA Prediction Model {version} — {model_type}"

    # Conectar a Neon
    database_url = db_config.get_database_url()
    sys_schema = db_config.get_schema("sys")
    engine = create_engine(database_url, pool_pre_ping=True, echo=False)

    with engine.begin() as conn:
        # Verificar si ya existe
        existing = conn.execute(text(
            f"SELECT id FROM {sys_schema}.model_versions WHERE version = :version"
        ), {"version": version}).fetchone()

        if existing:
            # Actualizar registro existente
            conn.execute(text(f"""
                UPDATE {sys_schema}.model_versions
                SET description = :description,
                    model_metadata = :metadata,
                    updated_at = :updated_at
                WHERE version = :version
            """), {
                "description": description,
                "metadata": json.dumps(metadata_json),
                "updated_at": datetime.now(timezone.utc),
                "version": version,
            })
            print(f"Versión actualizada: {version}")
        else:
            # Insertar nueva versión
            conn.execute(text(f"""
                INSERT INTO {sys_schema}.model_versions
                    (version, description, model_metadata, is_active, created_at)
                VALUES
                    (:version, :description, :metadata, :is_active, :created_at)
            """), {
                "version": version,
                "description": description,
                "metadata": json.dumps(metadata_json),
                "is_active": False,
                "created_at": datetime.now(timezone.utc),
            })
            print(f"Versión registrada: {version}")

        # Activar si se solicitó
        if activate:
            # Desactivar todas las versiones actuales
            conn.execute(text(
                f"UPDATE {sys_schema}.model_versions SET is_active = FALSE"
            ))
            # Activar la nueva
            conn.execute(text(
                f"UPDATE {sys_schema}.model_versions SET is_active = TRUE WHERE version = :version"
            ), {"version": version})
            print(f"Versión activada: {version}")
            print("Todas las demás versiones han sido desactivadas.")

    print("\nRegistro completado.")
    if activate:
        print(f"El Backend ahora usará el modelo {version} en la próxima solicitud.")


def activate_version(version: str):
    """Activa una versión ya registrada."""
    database_url = db_config.get_database_url()
    sys_schema = db_config.get_schema("sys")
    engine = create_engine(database_url, pool_pre_ping=True, echo=False)

    with engine.begin() as conn:
        # Verificar que existe
        existing = conn.execute(text(
            f"SELECT id FROM {sys_schema}.model_versions WHERE version = :version"
        ), {"version": version}).fetchone()

        if not existing:
            print(f"Error: la versión {version} no existe en la base de datos.")
            print("Ejecutar primero: python scripts/register_model_version.py --version {version}")
            sys.exit(1)

        conn.execute(text(
            f"UPDATE {sys_schema}.model_versions SET is_active = FALSE"
        ))
        conn.execute(text(
            f"UPDATE {sys_schema}.model_versions SET is_active = TRUE WHERE version = :version"
        ), {"version": version})

    print(f"Versión {version} activada exitosamente.")


def list_versions():
    """Lista todas las versiones registradas."""
    database_url = db_config.get_database_url()
    sys_schema = db_config.get_schema("sys")
    engine = create_engine(database_url, pool_pre_ping=True, echo=False)

    with engine.connect() as conn:
        rows = conn.execute(text(
            f"SELECT version, is_active, description, created_at FROM {sys_schema}.model_versions ORDER BY created_at DESC"
        )).fetchall()

    if not rows:
        print("No hay versiones registradas.")
        return

    print(f"\n{'Versión':<12} {'Activa':<8} {'Descripción':<40} {'Creado'}")
    print("-" * 80)
    for row in rows:
        active = "✅ SÍ" if row[1] else "   No"
        print(f"{row[0]:<12} {active:<8} {str(row[2])[:40]:<40} {str(row[3])[:19]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gestionar versiones de modelos ML")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--version",       help="Registrar esta versión (ej: v1.0.0)")
    group.add_argument("--activate-only", help="Solo activar una versión ya registrada")
    group.add_argument("--list",          action="store_true", help="Listar todas las versiones")

    parser.add_argument("--activate",    action="store_true", help="Activar la versión al registrarla")
    parser.add_argument("--description", default=None,        help="Descripción del modelo")

    args = parser.parse_args()

    if args.list:
        list_versions()
    elif args.activate_only:
        activate_version(args.activate_only)
    else:
        register_model_version(
            version=args.version,
            activate=args.activate,
            description=args.description,
        )
