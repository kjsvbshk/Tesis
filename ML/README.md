# ML — Módulo de Machine Learning

Módulo de entrenamiento, validación, evaluación y exportación de modelos de predicción para partidos NBA. Produce archivos `.joblib` que el Backend consume en tiempo real para generar predicciones.

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
├── requirements.txt
├── .env                             # Compartido con Backend (credenciales Neon)
│
├── src/
│   ├── config.py                    # Lee .env y construye URLs de conexión
│   ├── data_loader.py               # Carga datos desde Neon PostgreSQL
│   ├── db_ml.py                     # Utilidades específicas para el schema ml
│   ├── etl/
│   │   ├── build_features.py        # FASE 2: Feature engineering completo
│   │   └── validate_data_quality.py # FASE 3: Validación de calidad del dataset
│   ├── models/
│   │   ├── ensemble.py              # NBAEnsemble v2.1.0 (RF + XGBoost + Poisson → meta-modelo)
│   │   ├── random_forest.py         # NBARandomForest (clasificación calibrada)
│   │   ├── xgboost_model.py         # NBAXGBoost (regresión dual de scores)
│   │   ├── poisson_model.py         # NBABivariatePoisson (Karlis & Ntzoufras 2003)  ← v2.1.0
│   │   ├── margin_model.py          # NBAMarginModel (regresión de margen)
│   │   └── total_model.py           # NBATotalModel (regresión de total puntos)
│   ├── training/
│   │   └── train.py                 # Pipeline completo de entrenamiento
│   └── evaluation/
│       ├── metrics.py               # Log Loss, Brier, ROC-AUC, ECE, MAE, calibración
│       └── validation.py            # Validación temporal, criterios de aceptación
│
├── scripts/
│   ├── init_ml_schema.py            # Crear schema ml en Neon
│   ├── create_ml_ready_games.py     # FASE 1: Crear y poblar ml_ready_games
│   ├── export_model.py              # Exportar modelo a Backend/ml/models/
│   ├── register_model_version.py    # Registrar versión en sys.model_versions
│   ├── deploy_model.py              # Deploy automatizado (export + register + activate)
│   ├── compare_models.py            # Comparar métricas entre versiones
│   ├── backtesting.py               # Simulación de apuestas históricas
│   ├── baselines.py                 # Comparar modelo vs baselines (always_home, random)
│   ├── plot_calibration.py          # Generar gráficas de calibración
│   └── plot_backtesting.py          # Generar gráficas de backtesting
│
├── docs/
│   ├── features.md                  # Descripción detallada de las 33 features (v2.0.0)
│   ├── evaluation.md                # Métricas, criterios de aceptación, resultados
│   ├── limitations.md               # Limitaciones conocidas del modelo
│   ├── pipeline.md                  # Descripción del pipeline completo
│   ├── poisson_model.md             # Modelo Bivariate Poisson (v2.1.0)
│   └── roadmap.md                   # Hoja de ruta: Niveles 1-4 de predicción
│
├── models/
│   ├── nba_prediction_model_v*.joblib   # Modelos entrenados
│   └── metadata/                        # Métricas y metadatos por versión (JSON)
│       ├── v1.0.0_metadata.json ... v1.6.0_metadata.json
│       └── v2.0.0_metadata.json
│
└── reports/
    ├── backtesting_results*.json        # Resultados de backtesting por versión
    ├── baselines_comparison*.json       # Comparación vs baselines
    └── figures/                         # Gráficas generadas
        ├── calibration_*.png
        ├── confusion_matrix_*.png
        ├── cumulative_profit_*.png
        └── ...
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

### Fase 1 — Tabla Base `ml_ready_games` ✅ COMPLETADA

**Objetivo**: Crear una fila por partido con columnas base tomadas de `espn.games`.

```bash
python scripts/init_ml_schema.py
python scripts/create_ml_ready_games.py
```

**Resultado**: ~1,237 registros en `ml.ml_ready_games`.

---

### Fase 2 — Feature Engineering ✅ COMPLETADA

**Objetivo**: Calcular todas las features temporales y contextuales.

**Script principal**: `src/etl/build_features.py`

Todas las features rolling se calculan **solo con partidos anteriores** a la fecha del juego para evitar data leakage (garantizado con `shift(1)`).

```bash
python src/etl/build_features.py
```

---

### Fase 3 — Validación de Calidad del Dataset ✅ COMPLETADA

**Objetivo**: Garantizar que el dataset no tenga fugas de información ni problemas estructurales.

| Validación | Resultado |
|------------|-----------|
| No data leakage | Ninguna feature usa información posterior al partido |
| Nulos en target | `home_win` 100% completo |
| Distribución del target | 56.99% victorias locales (aceptable) |
| Duplicados | Sin registros duplicados |

```bash
python src/etl/validate_data_quality.py
```

---

### Fase 4 — Entrenamiento de Modelos ✅ COMPLETADA

#### Arquitectura del Ensamble (v2.1.0)

| Componente | Clase | Tipo | Output |
|-----------|-------|------|--------|
| `NBARandomForest` | `src/models/random_forest.py` | Clasificación calibrada | P(home_win) |
| `NBAXGBoost` | `src/models/xgboost_model.py` | Regresión dual | (home_score, away_score) |
| `NBABivariatePoisson` | `src/models/poisson_model.py` | Modelo de conteo bivariante | P(home_win), λ₁, λ₂, λ₃ |
| `NBAEnsemble` | `src/models/ensemble.py` | Stacking 3 base-learners → LogReg + Isotonic | P(home_win) calibrado |
| `NBAMarginModel` | `src/models/margin_model.py` | Regresión | Margen esperado (pts) |
| `NBATotalModel` | `src/models/total_model.py` | Regresión | Total puntos esperados |

El meta-vector del ensemble en v2.1.0 es 3-dimensional: `[rf_proba, score_diff, poisson_proba]`.

#### Versiones de Modelos

| Versión | Features | Base learners | Estado | Log Loss | Brier | ROC-AUC | ECE | Aprobado |
|---------|----------|---------------|--------|----------|-------|---------|-----|---------|
| v1.6.0 | 21 | RF + XGBoost | Producción anterior | 0.6553 | 0.2312 | 0.6542 | 0.0363 | ✅ Todos |
| v2.0.0 | 33 | RF + XGBoost | No integrado | 0.6855 | 0.2430 | 0.6462 | 0.0925 | ❌ Parcial |
| **v2.1.0** | **33** | **RF + XGBoost + Bivariate Poisson** | **Pendiente entrenamiento contra Neon** | — | — | — | — | — |

**v1.6.0** sigue siendo el modelo activo hasta que v2.1.0 sea entrenado en producción y supere los criterios de aceptación.

**v2.1.0** introduce el modelo Bivariate Poisson (Karlis & Ntzoufras, 2003) como tercer base-learner. Detalles en `docs/poisson_model.md`.

#### Tests automatizados (v2.1.0)

```bash
cd ML
python -m unittest tests.test_poisson_model -v       # 16 tests del modelo Poisson
python -m unittest tests.test_ensemble_v2_1_0 -v     # 4 smoke tests del ensemble
python tests/benchmark_v2_1_0.py                     # Benchmark sintético
```

#### Criterios de Aceptación

| Métrica | Umbral | Justificación |
|---------|--------|---------------|
| Log Loss | < 0.68 | Calidad de probabilidades |
| Brier Score | < 0.25 | Calibración cuadrática |
| ROC-AUC | > 0.55 | Poder discriminativo |
| ECE | < 0.05 | Calibración probabilística |

---

## Estructura de Salida del Modelo

El objeto `.joblib` retorna al ser invocado con un vector de features:

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

### Ejecutar pipeline completo desde cero

```bash
# Fase 1 — Crear tabla base
python scripts/init_ml_schema.py
python scripts/create_ml_ready_games.py

# Fase 2 — Feature engineering
python src/etl/build_features.py

# Fase 3 — Validación
python src/etl/validate_data_quality.py
```

### Entrenar modelo

```bash
# Ensemble v2.1.0 (default — RF + XGBoost + Bivariate Poisson)
python -m src.training.train --version v2.1.0 --model ensemble

# Modelos aislados (para benchmarking)
python -m src.training.train --version v2.1.0-rf      --model rf
python -m src.training.train --version v2.1.0-xgb     --model xgb
python -m src.training.train --version v2.1.0-poisson --model poisson
```

```python
from src.training.train import train_model
model, metrics, path = train_model(version="v2.1.0", model_type="ensemble")
```

### Exportar y registrar versión

```bash
# Export + registro + activación en un paso
python scripts/deploy_model.py --version v1.6.0 --activate

# O paso a paso:
python scripts/export_model.py --version v1.6.0
python scripts/register_model_version.py --version v1.6.0 --activate
```

### Evaluar y comparar modelos

```bash
# Comparar métricas entre versiones
python scripts/compare_models.py

# Backtesting de simulación de apuestas
python scripts/backtesting.py

# Comparar vs baselines (always_home, random)
python scripts/baselines.py

# Gráficas de calibración
python scripts/plot_calibration.py

# Gráficas de backtesting
python scripts/plot_backtesting.py
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
2. Verificar que pasa todos los criterios de aceptación
3. Ejecutar `python scripts/deploy_model.py --version vX.X.X --activate`

---

## Documentación Adicional

| Documento | Contenido |
|-----------|-----------|
| `docs/features.md` | Descripción detallada de las 33 features de v2.0.0 |
| `docs/evaluation.md` | Métricas, criterios de aceptación, resultados por versión |
| `docs/limitations.md` | Limitaciones conocidas y advertencias |
| `docs/pipeline.md` | Pipeline completo de datos y entrenamiento |
| `docs/roadmap.md` | Hoja de ruta: Niveles 1-4 (moneyline → props de jugador) |

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

## Consideraciones Técnicas

- **Temporal ordering**: Todas las features rolling usan `shift(1)` para garantizar que solo se usan datos de partidos anteriores. Validado explícitamente en la Fase 3.
- **Idempotencia del ETL**: `build_features.py` puede ejecutarse múltiples veces. Detecta registros existentes y solo actualiza los que tienen features NULL o desactualizadas.
- **Criterio de promoción**: Una versión solo se activa en producción si pasa **todos** los criterios de aceptación y se evalúa sobre el mismo test set temporal para comparación justa.
- **Calibración**: El modelo v1.6.0 usa calibración Isotonic Regression para garantizar que las probabilidades reportadas sean realistas (ECE = 0.036).

---

**Última actualización**: Abril 2026
