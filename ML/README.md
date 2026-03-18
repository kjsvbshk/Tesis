# ML — Módulo de Machine Learning

Módulo de entrenamiento, validación y exportación de modelos de predicción para partidos NBA. Produce archivos `.joblib` que el Backend consume en tiempo real para generar predicciones.

---

## Posición en el Sistema

```
Scrapping → [espn schema en Neon] → ML → [modelo .joblib] → Backend → Frontend
```

Este módulo es el único que escribe en el schema `ml` de Neon y el único que genera los archivos de modelo que consume el Backend.

---

## Estructura del Directorio

```
ML/
├── README.md
├── CONTEXT.md                       # Resumen ejecutivo del contexto del proyecto
├── requirements.txt
├── .env                             # Compartido con Backend (credenciales Neon)
│
├── src/
│   ├── config.py                    # Lee .env y construye URLs de conexión
│   ├── data_loader.py               # Carga datos desde Neon PostgreSQL
│   ├── db_ml.py                     # Utilidades específicas para el schema ml
│   └── etl/
│       ├── build_features.py        # FASE 2: Feature engineering completo
│       └── validate_data_quality.py # FASE 3: Validación de calidad del dataset
│
├── scripts/
│   ├── init_ml_schema.py            # Crear schema ml en Neon
│   ├── create_ml_ready_games.py     # FASE 1: Crear y poblar ml_ready_games
│   ├── verify_ml_ready_games.py     # Verificar estructura de la tabla base
│   ├── verify_features.py           # Verificar features calculadas
│   ├── check_phase2.py              # Checks finales de Fase 2
│   ├── phase3_summary.py            # Resumen ejecutivo de Fase 3
│   ├── test_connection.py           # Probar conexión a Neon
│   ├── export_model.py              # Exportar modelo a Backend/ml/models/
│   ├── register_model_version.py    # Registrar versión en sys.model_versions
│   └── compare_models.py            # Comparar métricas entre versiones
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_model_evaluation.ipynb
│
├── data/
│   ├── raw/                         # Datos sin procesar
│   ├── processed/                   # Datasets procesados
│   └── features/                    # Outputs de feature engineering
│
└── models/
    ├── nba_prediction_model_v*.joblib
    └── metadata/                    # Métricas y metadatos por versión
```

---

## Pipeline de Datos

### Fuente: Schema `espn` en Neon
Datos cargados por el módulo Scrapping:

| Tabla | Contenido | Uso en ML |
|-------|-----------|-----------|
| `espn.games` | Resultados de partidos (fecha, equipos, scores) | Base de `ml_ready_games` |
| `espn.team_stats` | Estadísticas ofensivas/defensivas por equipo | Features de rendimiento |
| `espn.standings` | Clasificaciones por temporada | Win/loss record |
| `espn.injuries` | Reportes de lesiones activas | Feature `injury_count` |
| `espn.odds` | Cuotas de apuestas | Probabilidades implícitas |

### Destino: Schema `ml` en Neon
Tabla central del módulo:

**`ml.ml_ready_games`** — Una fila por partido, con todas las features listas para entrenar.

---

## Fases de Desarrollo

### Fase 1 — Tabla Base `ml_ready_games` (COMPLETADA)

**Objetivo**: Crear una fila por partido con columnas base tomadas de `espn.games`.

**Script principal**: `scripts/create_ml_ready_games.py`

Columnas base creadas:
- `game_id`, `fecha`, `season`
- `home_team_id`, `away_team_id`
- `home_score`, `away_score`
- `home_win` (target — booleano derivado de scores)
- Columnas placeholder para features (NULL inicialmente)

**Resultado**: 1,237 registros en `ml.ml_ready_games`.

```bash
python scripts/init_ml_schema.py
python scripts/create_ml_ready_games.py
python scripts/verify_ml_ready_games.py
```

---

### Fase 2 — Feature Engineering (COMPLETADA)

**Objetivo**: Calcular todas las features temporales y contextuales.

**Script principal**: `src/etl/build_features.py`

#### Features implementadas

**Rolling Statistics (ventanas temporales)**
- `home_ppg_last5` / `away_ppg_last5` — Puntos por partido, últimos 5 juegos
- `home_ppg_last10` / `away_ppg_last10` — Últimos 10 juegos
- `home_net_rating_last5` / `away_net_rating_last5` — Net rating (ofensivo - defensivo)
- `home_net_rating_last10` / `away_net_rating_last10`

> Las ventanas rolling se calculan **solo con partidos anteriores** a la fecha del juego para evitar data leakage.

**Rest Days**
- `home_rest_days` — Días desde el último partido del equipo local
- `away_rest_days` — Días desde el último partido del equipo visitante
- Cobertura: 99% de los registros

**Injury Count**
- `home_injuries_count` — Número de lesiones activas del equipo local
- `away_injuries_count` — Número de lesiones activas del equipo visitante
- Cobertura: 100% de los registros

**Implied Probabilities (desde odds)**
- `implied_prob_home` — Probabilidad implícita de victoria local derivada de cuotas
- `implied_prob_away` — Probabilidad implícita de victoria visitante
- Cobertura: ~1% (limitado por disponibilidad de datos de odds)

El script es **idempotente**: puede ejecutarse múltiples veces sin duplicar ni corromper datos.

```bash
python src/etl/build_features.py
python scripts/verify_features.py
python scripts/check_phase2.py
```

---

### Fase 3 — Validación de Calidad del Dataset (COMPLETADA)

**Objetivo**: Garantizar que el dataset no tenga fugas de información ni problemas estructurales.

**Script principal**: `src/etl/validate_data_quality.py`

#### Validaciones realizadas

| Validación | Resultado |
|------------|-----------|
| **No data leakage** | Ninguna feature usa información posterior a la fecha del partido |
| **Nulos en target** | `home_win` sin ningún NULL (100% completo) |
| **Distribución del target** | 56.99% victorias locales / 43.01% visitantes (aceptable) |
| **Integridad de joins** | Todos los `game_id` presentes en `espn.games` |
| **Rangos de valores** | Features dentro de rangos esperados sin outliers extremos |
| **Duplicados** | Sin registros duplicados |

```bash
python src/etl/validate_data_quality.py
python scripts/phase3_summary.py
```

---

### Fase 4 — Entrenamiento de Modelos (EN DESARROLLO)

#### Modelos del Ensamble

**RandomForest (Clasificación)**
- Predice resultado binario: victoria local (`home_win = True/False`)
- Output: probabilidad `[P(away_win), P(home_win)]`
- Hiperparámetros clave: `n_estimators`, `max_depth`, `min_samples_split`

**XGBoost (Regresión)**
- Predice puntuación esperada de cada equipo
- Output: `predicted_home_score`, `predicted_away_score`

**Stacking Ensemble**
- Meta-modelo que combina outputs de RandomForest y XGBoost
- Produce predicción final con mayor confianza

#### Estructura de salida del modelo

El objeto `.joblib` debe retornar al ser invocado:

```python
{
    "home_win_probability": float,    # 0.0 – 1.0
    "away_win_probability": float,    # 0.0 – 1.0
    "predicted_home_score": float,
    "predicted_away_score": float,
    "predicted_total": float,
    "recommended_bet": str,           # "home" | "away" | "none"
    "expected_value": float,
    "confidence_score": float,        # 0.0 – 1.0
    "model_version": str,
    "prediction_timestamp": datetime,
    "features_used": dict
}
```

---

## Guía de Uso

### Instalación

```bash
cd ML
pip install -r requirements.txt
```

El módulo usa el mismo `.env` que el Backend (ubicado en la raíz del repositorio). Asegurarse de que las variables `NEON_*` estén configuradas.

### Probar conexión

```bash
python scripts/test_connection.py
```

### Ejecutar pipeline completo desde cero

```bash
# Fase 1 — Crear tabla base
python scripts/init_ml_schema.py
python scripts/create_ml_ready_games.py

# Fase 2 — Feature engineering
python src/etl/build_features.py

# Fase 3 — Validación
python src/etl/validate_data_quality.py
python scripts/phase3_summary.py
```

### Cargar datos manualmente

```python
from src.data_loader import DataLoader

loader = DataLoader(schema="espn")

# Cargar partidos de una temporada
games = loader.load_games(
    season_start="2023-10-01",
    season_end="2024-06-30"
)

# Cargar estadísticas de equipos
team_stats = loader.load_team_stats(season="2023-24")

# Cargar dataset consolidado
df = loader.load_consolidated_dataset(
    season_start="2023-10-01",
    season_end="2024-06-30"
)
```

### Entrenar y exportar modelo

```python
from src.training.train import train_model
from scripts.export_model import export_model

model, metrics = train_model(data=df, model_type="ensemble", version="v1.0.0")
export_model(model, version="v1.0.0", metrics=metrics)
# → Copia a Backend/ml/models/nba_prediction_model_v1.0.0.joblib
```

### Registrar versión en Backend

```python
from scripts.register_model_version import register_model_version

register_model_version(
    version="v1.0.0",
    model_path="models/nba_prediction_model_v1.0.0.joblib",
    metadata=metrics,
    description="Ensamble RandomForest + XGBoost, Fase 4",
    activate=True
)
```

---

## Integración con el Backend

El Backend carga el modelo desde:
```
Backend/ml/models/nba_prediction_model_{version}.joblib
```

La versión activa se determina consultando `sys.model_versions WHERE is_active = TRUE`.

Para desplegar una nueva versión:
1. Entrenar modelo → `ML/models/nba_prediction_model_vX.X.X.joblib`
2. Copiar a `Backend/ml/models/`
3. Ejecutar `register_model_version.py` con `activate=True`

---

## Variables de Entorno

```bash
# Neon PostgreSQL (mismo .env que Backend)
NEON_DB_HOST=...
NEON_DB_PORT=5432
NEON_DB_NAME=...
NEON_DB_USER=...
NEON_DB_PASSWORD=...
NEON_DB_SSLMODE=require
NEON_DB_CHANNEL_BINDING=require

# Schemas
NBA_DB_SCHEMA=espn
DB_SCHEMA=sys
ML_DB_SCHEMA=ml
```

---

## Tests

```bash
pytest tests/
pytest tests/ --cov=src --cov-report=html
```

---

## Consideraciones Técnicas

- **Temporal ordering**: Todas las features rolling se calculan exclusivamente con partidos anteriores a la fecha del juego. Esto es validado explícitamente en la Fase 3.
- **Idempotencia del ETL**: `build_features.py` puede ejecutarse múltiples veces. Detecta registros existentes y solo actualiza los que tienen features NULL o desactualizadas.
- **Escalabilidad temporal**: A medida que se agregan nuevas temporadas, solo es necesario re-ejecutar `build_features.py` — la tabla base se actualiza automáticamente.
- **Validación del modelo**: Se recomienda evaluar el modelo con datos de temporadas no vistas durante el entrenamiento (validación temporal, no aleatoria).

---

**Última actualización**: Marzo 2026
