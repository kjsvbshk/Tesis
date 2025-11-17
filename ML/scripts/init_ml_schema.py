#!/usr/bin/env python3
"""
Script para inicializar el esquema ML en Neon
Crea el esquema 'ml' y las tablas necesarias para la fase 1
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from src.config import db_config


def create_ml_schema():
    """
    Crea el esquema ML en Neon
    """
    # Obtener URL de conexión (solo Neon)
    database_url = db_config.get_database_url()
    schema_name = db_config.get_schema("ml")
    
    print("=" * 60)
    print(f"🔧 Inicializando Esquema ML (Fase 1) en Neon")
    print("=" * 60)
    print(f"Base de datos: Neon (cloud)")
    print(f"Esquema: {schema_name}")
    print()
    
    # Crear engine
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            # Verificar si el esquema ya existe
            check_schema_query = text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = :schema_name
            """)
            result = conn.execute(check_schema_query, {"schema_name": schema_name})
            schema_exists = result.fetchone() is not None
            
            if schema_exists:
                print(f"✅ El esquema '{schema_name}' ya existe")
            else:
                # Crear esquema
                print(f"📝 Creando esquema '{schema_name}'...")
                create_schema_query = text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                conn.execute(create_schema_query)
                conn.commit()
                print(f"✅ Esquema '{schema_name}' creado exitosamente")
            
            print()
            
            # Crear tablas para Fase 1
            print("📋 Creando tablas para Fase 1...")
            print()
            
            # Tabla: experimentos (para trackear experimentos de ML)
            create_experiments_table = text(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.experiments (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    phase VARCHAR(50) NOT NULL DEFAULT 'phase_1',
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    metadata JSONB,
                    UNIQUE(name, phase)
                );
            """)
            
            conn.execute(create_experiments_table)
            print("  ✅ Tabla 'experiments' creada")
            
            # Tabla: training_runs (para trackear ejecuciones de entrenamiento)
            create_training_runs_table = text(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.training_runs (
                    id SERIAL PRIMARY KEY,
                    experiment_id INTEGER REFERENCES {schema_name}.experiments(id) ON DELETE CASCADE,
                    model_type VARCHAR(100) NOT NULL,
                    version VARCHAR(50),
                    status VARCHAR(50) NOT NULL DEFAULT 'running',
                    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    metrics JSONB,
                    hyperparameters JSONB,
                    training_data_info JSONB,
                    model_path TEXT,
                    notes TEXT
                );
            """)
            
            conn.execute(create_training_runs_table)
            print("  ✅ Tabla 'training_runs' creada")
            
            # Tabla: model_evaluations (para evaluaciones de modelos)
            create_evaluations_table = text(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.model_evaluations (
                    id SERIAL PRIMARY KEY,
                    training_run_id INTEGER REFERENCES {schema_name}.training_runs(id) ON DELETE CASCADE,
                    evaluation_type VARCHAR(50) NOT NULL,
                    split_type VARCHAR(50),
                    metrics JSONB NOT NULL,
                    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                );
            """)
            
            conn.execute(create_evaluations_table)
            print("  ✅ Tabla 'model_evaluations' creada")
            
            # Tabla: feature_importance (para almacenar importancia de features)
            create_feature_importance_table = text(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.feature_importance (
                    id SERIAL PRIMARY KEY,
                    training_run_id INTEGER REFERENCES {schema_name}.training_runs(id) ON DELETE CASCADE,
                    feature_name VARCHAR(255) NOT NULL,
                    importance_score FLOAT NOT NULL,
                    importance_type VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(training_run_id, feature_name, importance_type)
                );
            """)
            
            conn.execute(create_feature_importance_table)
            print("  ✅ Tabla 'feature_importance' creada")
            
            # Tabla: predictions_validation (para validar predicciones con resultados reales)
            create_predictions_validation_table = text(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.predictions_validation (
                    id SERIAL PRIMARY KEY,
                    training_run_id INTEGER REFERENCES {schema_name}.training_runs(id) ON DELETE CASCADE,
                    game_id INTEGER,
                    predicted_home_score FLOAT,
                    predicted_away_score FLOAT,
                    predicted_home_win_probability FLOAT,
                    actual_home_score INTEGER,
                    actual_away_score INTEGER,
                    actual_home_win BOOLEAN,
                    prediction_error FLOAT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            conn.execute(create_predictions_validation_table)
            print("  ✅ Tabla 'predictions_validation' creada")
            
            # Índices para mejorar performance
            print()
            print("📊 Creando índices...")
            
            indexes = [
                f"CREATE INDEX IF NOT EXISTS idx_experiments_phase ON {schema_name}.experiments(phase)",
                f"CREATE INDEX IF NOT EXISTS idx_experiments_status ON {schema_name}.experiments(status)",
                f"CREATE INDEX IF NOT EXISTS idx_training_runs_experiment ON {schema_name}.training_runs(experiment_id)",
                f"CREATE INDEX IF NOT EXISTS idx_training_runs_status ON {schema_name}.training_runs(status)",
                f"CREATE INDEX IF NOT EXISTS idx_evaluations_training_run ON {schema_name}.model_evaluations(training_run_id)",
                f"CREATE INDEX IF NOT EXISTS idx_feature_importance_training_run ON {schema_name}.feature_importance(training_run_id)",
                f"CREATE INDEX IF NOT EXISTS idx_predictions_validation_training_run ON {schema_name}.predictions_validation(training_run_id)",
                f"CREATE INDEX IF NOT EXISTS idx_predictions_validation_game ON {schema_name}.predictions_validation(game_id)",
            ]
            
            for index_sql in indexes:
                conn.execute(text(index_sql))
            
            print("  ✅ Índices creados")
            
            conn.commit()
            
            print()
            print("=" * 60)
            print("✅ Esquema ML inicializado exitosamente en Neon")
            print("=" * 60)
            print()
            print("📋 Tablas creadas:")
            print("  - experiments")
            print("  - training_runs")
            print("  - model_evaluations")
            print("  - feature_importance")
            print("  - predictions_validation")
            print()
            
    except Exception as e:
        print(f"❌ Error al inicializar esquema ML: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Función principal"""
    create_ml_schema()


if __name__ == "__main__":
    main()
