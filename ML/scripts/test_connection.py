#!/usr/bin/env python3
"""
Script para probar la conexión a Neon
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import DataLoader
from src.config import db_config
from src.db_ml import MLDatabase


def test_connections():
    """Prueba conexiones a Neon"""
    
    print("=" * 60)
    print("🔌 Prueba de Conexiones a Neon (Cloud)")
    print("=" * 60)
    print()
    
    if not db_config.NEON_DB_HOST:
        print("❌ NEON_DB_HOST no está configurado en .env")
        print("   Asegúrate de tener las variables NEON_* configuradas")
        return
    
    # Test 1: Esquema ESPN (datos NBA)
    print("1️⃣  Probando conexión a esquema ESPN (datos NBA)...")
    loader_espn = DataLoader(schema="espn")
    success_espn = loader_espn.test_connection()
    print(f"   Esquema: {loader_espn.schema}")
    print()
    
    # Test 2: Esquema APP/SYS (datos del sistema)
    print("2️⃣  Probando conexión a esquema APP/SYS (datos del sistema)...")
    loader_app = DataLoader(schema="app")
    success_app = loader_app.test_connection()
    print(f"   Esquema: {loader_app.schema}")
    print()
    
    # Test 3: Esquema ML
    print("3️⃣  Probando conexión a esquema ML...")
    ml_db = MLDatabase()
    success_ml = ml_db.test_connection()
    print(f"   Esquema: {ml_db.schema}")
    print()
    
    # Resumen
    print("=" * 60)
    print("📊 Resumen")
    print("=" * 60)
    print(f"Neon - ESPN (datos NBA):  {'✅ OK' if success_espn else '❌ FALLO'}")
    print(f"Neon - APP/SYS (sistema): {'✅ OK' if success_app else '❌ FALLO'}")
    print(f"Neon - ML (esquema ml):   {'✅ OK' if success_ml else '❌ FALLO'}")
    print()
    
    # Test de carga de datos
    if success_espn:
        print("=" * 60)
        print("📥 Probando carga de datos desde ESPN...")
        print("=" * 60)
        try:
            games = loader_espn.load_games(limit=5)
            print(f"✅ Cargados {len(games)} partidos de prueba")
            if not games.empty:
                print(f"   Columnas disponibles: {list(games.columns)[:5]}...")
        except Exception as e:
            print(f"⚠️  Error al cargar datos: {e}")
            print("   (Esto puede ser normal si las tablas tienen estructura diferente)")
        print()


if __name__ == "__main__":
    test_connections()
