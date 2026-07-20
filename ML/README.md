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
│   │   ├── ensemble.py              # NBAEnsemble v3.1.0 (RF + XGB + Poisson → meta-modelo 4D + props)
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
│   ├── register_model_version.py    # Registrar versión en app.model_versions
│   ├── deploy_model.py              # Deploy automatizado (export + register + activate)
│   ├── compare_models.py            # Comparar métricas entre versiones
│   ├── backtesting.py               # Simulación de apuestas históricas
│   ├── baselines.py                 # Comparar modelo vs baselines (always_home, random)
│   ├── plot_calibration.py          # Generar gráficas de calibración
│   └── plot_backtesting.py          # Generar gráficas de backtesting
│
├── docs/
│   ├── features.md                  # Descripción detallada de las features (52 en v3.1.0)
│   ├── evaluation.md                # Métricas, criterios de aceptación, resultados
│   ├── limitations.md               # Limitaciones conocidas del modelo
│   ├── pipeline.md                  # Descripción del pipeline completo
│   ├── poisson_model.md             # Modelo Bivariate Poisson (v2.1.0)
│   ├── model_specification.md       # Especificación formal del modelo
│   └── v2_1_0_release_notes.md      # Notas históricas de calibración v2.1.x
│
├── models/
│   ├── nba_prediction_model_v*.joblib   # Modelos entrenados
│   └── metadata/                        # Métricas y metadatos por versión (JSON)
│       ├── v1.0.0_metadata.json ... v3.1.0_metadata.json
│       └── (una por versión entrenada)
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

#### Arquitectura del Ensamble (v2.1.2+, vigente en v3.1.0)

| Componente | Clase | Tipo | Output |
|-----------|-------|------|--------|
| `NBARandomForest` | `src/models/random_forest.py` | Clasificación calibrada | P(home_win) |
| `NBAXGBoost` | `src/models/xgboost_model.py` | Regresión dual | (home_score, away_score) |
| `NBABivariatePoisson` | `src/models/poisson_model.py` | Modelo de conteo bivariante | μ_diff, σ_diff, λ₁, λ₂, λ₃ |
| `NBAEnsemble` | `src/models/ensemble.py` | Stacking OOF temporal → StandardScaler+LogReg + Isotonic | P(home_win) calibrado |
| `NBAMarginModel` | `src/models/margin_model.py` | Regresión | Margen esperado (pts) |
| `NBATotalModel` | `src/models/total_model.py` | Regresión | Total puntos esperados |
| `NBAStatRegressor` ×10 | `src/models/stat_regressor.py` | Regresión (team-props v2.2.0+) | reb/ast/stl/blk/to por equipo |

El meta-vector del ensemble desde v2.1.2 es 4-dimensional: `[rf_proba, score_diff, poisson_mu_diff, poisson_sigma_diff]`. El Poisson NO aporta probabilidad al meta-learner (corrección del overconfidence ECE=0.084 de v2.1.0).

#### Versiones de Modelos

| Versión | Features | Base learners | Estado | Log Loss | Brier | ROC-AUC | ECE | Aprobado |
|---------|----------|---------------|--------|----------|-------|---------|-----|---------|
| v1.6.0 | 21 | RF + XGBoost | Histórica | 0.6553 | 0.2312 | 0.6542 | 0.0363 | ✅ Todos |
| v2.2.0 | 35 | RF + XGB + Poisson (+props) | Histórica | 0.6145 | 0.2130 | 0.7124 | 0.0106 | ✅ Todos |
| v3.0.0 | 47 | RF + XGB + Poisson (+props) | Histórica | 0.6127 | 0.2123 | 0.7188 | 0.0353 | ✅ Todos |
| **v3.1.0** | **52** | **RF + XGB + Poisson (+props)** | **ACTIVA en producción** | **0.6174** | **0.2146** | **0.7096** | **0.0245** | ✅ Todos |

**v3.1.0** añade sobre v3.0.0: porcentajes de tiro rolling last-5 (`fg_pct_rolling_diff`, `fg3_pct_rolling_diff`, `ft_pct_rolling_diff`, doc §2.3.1) y probabilidades implícitas del mercado (`implied_prob_home/away`, doc §2.3.4, activadas por defecto; cobertura actual ~1.3%, pre-imputadas con mediana).

Detalles del Poisson (Karlis & Ntzoufras, 2003) en `docs/poisson_model.md`.

#### Tests automatizados

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
# Ensemble v3.1.0 (default — 52 features: V3 + shooting rolling + implied_prob)
python -m src.training.train

# Equivalente explícito
python -m src.training.train --version v3.1.0 --model ensemble

# Desactivar bloques de features (flags booleanos, activados por defecto)
python -m src.training.train --no-use-odds   # sin implied_prob_* (50 features)
python -m src.training.train --no-use-v3     # sin V3/V3.1 (35 features)

# Modelos aislados (para benchmarking)
python -m src.training.train --version v3.1.0-rf      --model rf
python -m src.training.train --version v3.1.0-xgb     --model xgb
python -m src.training.train --version v3.1.0-poisson --model poisson
```

```python
from src.training.train import train_model
model, metrics, path = train_model(version="v3.1.0", model_type="ensemble")
```

### Exportar y registrar versión

```bash
# Deploy completo: copia + registro en app.model_versions + activación
python -m scripts.deploy_model --version v3.1.0 --activate

# O paso a paso:
python scripts/export_model.py --version v3.1.0
python scripts/register_model_version.py --version v3.1.0 --activate

# Nota: si Backend/.env define MODEL_DIR=../ML/models (desarrollo local),
# el deploy omite la copia (origen == destino) y solo registra/activa.
# Tras activar, reiniciar el Backend (el modelo se carga en startup).
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

La versión activa se determina consultando `app.model_versions WHERE is_active = TRUE`.

Para desplegar una nueva versión:
1. Entrenar modelo → `ML/models/nba_prediction_model_vX.X.X.joblib`
2. Verificar que pasa todos los criterios de aceptación
3. Ejecutar `python scripts/deploy_model.py --version vX.X.X --activate`

---

## Documentación Adicional

| Documento | Contenido |
|-----------|-----------|
| `docs/features.md` | Descripción detallada de las features (52 en v3.1.0) |
| `docs/evaluation.md` | Métricas, criterios de aceptación, resultados por versión |
| `docs/limitations.md` | Limitaciones conocidas y advertencias |
| `docs/pipeline.md` | Pipeline completo de datos y entrenamiento |
| `docs/model_specification.md` | Especificación formal del modelo y umbrales |
| `docs/poisson_model.md` | Modelo Bivariate Poisson (Karlis & Ntzoufras) |
| `docs/v2_1_0_release_notes.md` | Notas históricas: corrección de calibración v2.1.x |

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
