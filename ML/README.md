# Machine Learning - Sistema de Predicciones NBA

## 📋 Contexto del Proyecto

Esta carpeta `ML/` es parte de un sistema completo de **predicciones y apuestas virtuales para la NBA**. El proyecto está compuesto por varios módulos que trabajan juntos:

### 🏗️ Arquitectura del Sistema

```
Tesis/
├── Backend/          # API FastAPI que usa los modelos ML para hacer predicciones
├── Frontend/         # Aplicación React/TypeScript para usuarios
├── Scrapping/        # Sistema de extracción de datos (NBA y Premier League)
└── ML/              # ← ESTA CARPETA: Entrenamiento y gestión de modelos ML
```

### 🔄 Flujo de Datos

1. **Scrapping** → Extrae datos de ESPN (partidos, estadísticas, lesiones, cuotas)
2. **ML** → Entrena modelos con datos históricos
3. **Backend** → Carga modelos entrenados y genera predicciones en tiempo real
4. **Frontend** → Muestra predicciones y permite apuestas virtuales

---

## 🎯 Objetivo de esta Carpeta

Esta carpeta `ML/` está diseñada para:

- **Entrenar modelos de machine learning** para predecir resultados de partidos NBA
- **Gestionar versiones de modelos** (versionado)
- **Evaluar y comparar modelos** (métricas, validación)
- **Exportar modelos entrenados** para uso en producción (Backend)

---

## 🤖 Modelos de Machine Learning

El sistema utiliza un **ensamble de modelos** para maximizar la precisión:

### 1. RandomForest
- **Tipo**: Clasificación
- **Objetivo**: Predecir quién ganará el partido (home/away)
- **Output**: Probabilidad de victoria de cada equipo

### 2. XGBoost
- **Tipo**: Regresión
- **Objetivo**: Predecir cuántos puntos anotará cada equipo
- **Output**: Puntuación esperada (home_score, away_score)

### 3. Stacking Ensemble
- **Tipo**: Meta-modelo
- **Objetivo**: Combinar predicciones de RandomForest y XGBoost
- **Output**: Predicción final con mayor confianza

---

## 📊 Características (Features) que Usan los Modelos

Los modelos analizan las siguientes características:

### Características de Equipos
- **Rendimiento reciente**: Últimos 5-10 partidos
- **Eficiencia ofensiva**: Puntos por posesión, % de tiros anotados
- **Eficiencia defensiva**: Puntos permitidos, robos, bloqueos
- **Estadísticas de temporada**: Win/Loss record, diferencia de puntos

### Características del Partido
- **Ventaja de localía**: Si juegan en casa o fuera
- **Días de descanso**: Cuántos días descansó cada equipo
- **Back-to-back**: Si un equipo juega partidos consecutivos
- **Head-to-head**: Historial entre los dos equipos

### Características Externas
- **Lesiones**: Jugadores lesionados y su importancia
- **Cuotas de apuestas**: Probabilidades de casas de apuestas
- **Forma reciente**: Tendencia de victorias/derrotas

---

## 📁 Estructura Recomendada

```
ML/
├── README.md                    # Este archivo
├── CONTEXT.md                   # Resumen ejecutivo del contexto
├── requirements.txt             # Dependencias específicas de ML
├── .gitignore                   # Archivos a ignorar en Git
│
├── data/                        # Datos para entrenamiento
│   ├── raw/                     # Datos sin procesar (referencia a Scrapping)
│   ├── processed/               # Datos procesados y listos para entrenar
│   └── features/                # Features engineering
│
├── notebooks/                   # Jupyter notebooks para exploración
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_model_evaluation.ipynb
│
├── src/                         # Código fuente de ML
│   ├── __init__.py
│   ├── config.py                # Configuración (lee .env)
│   ├── data_loader.py           # Cargar datos desde PostgreSQL
│   ├── feature_engineering.py   # Crear features
│   ├── models/                  # Definición de modelos
│   │   ├── __init__.py
│   │   ├── random_forest.py
│   │   ├── xgboost_model.py
│   │   └── ensemble.py
│   ├── training/                # Scripts de entrenamiento
│   │   ├── __init__.py
│   │   ├── train.py             # Script principal de entrenamiento
│   │   └── train_ensemble.py
│   └── evaluation/              # Evaluación de modelos
│       ├── __init__.py
│       ├── metrics.py
│       └── validation.py
│
├── scripts/                     # Scripts utilitarios
│   ├── test_connection.py       # Probar conexión a BD
│   ├── export_model.py          # Exportar modelo para Backend
│   ├── register_model_version.py # Registrar versión en BD
│   └── compare_models.py        # Comparar versiones
│
├── models/                      # Modelos entrenados (exportados)
│   ├── nba_prediction_model_v1.0.0.joblib
│   ├── nba_prediction_model_v1.1.0.joblib
│   └── metadata/                # Metadatos de cada modelo
│       ├── v1.0.0_metadata.json
│       └── v1.1.0_metadata.json
│
└── tests/                       # Tests unitarios
    ├── __init__.py
    ├── test_feature_engineering.py
    └── test_models.py
```

---

## 🔌 Integración con Backend

### Cómo el Backend Carga los Modelos

El Backend busca modelos en la ruta:
```
Backend/ml/models/nba_prediction_model_{version}.joblib
```

**Ejemplo:**
- Modelo versión `v1.0.0` → `Backend/ml/models/nba_prediction_model_v1.0.0.joblib`
- Si no encuentra versión específica → `Backend/ml/models/nba_prediction_model.joblib`

### Sistema de Versionado

El Backend usa la tabla `app.model_versions` (o `sys.model_versions` según configuración) para gestionar versiones:

```python
# ModelVersion en Backend/app/models/model_version.py
- id: int
- version: str (e.g., "v1.0.0")
- is_active: bool (solo una versión activa)
- model_metadata: JSON (métricas, features, etc.)
- description: str
- created_at: datetime
```

**Flujo de despliegue:**
1. Entrenar modelo en `ML/`
2. Exportar a `Backend/ml/models/`
3. Registrar versión en BD (tabla `model_versions`)
4. Activar versión (marcar `is_active=True`)

---

## 📚 Fuentes de Datos

### Base de Datos Neon (Cloud)

El sistema usa **Neon PostgreSQL** (cloud) con múltiples esquemas:

1. **Esquema `espn`**: Datos extraídos por Scrapping
   - `games` - Partidos y resultados
   - `team_stats` - Estadísticas de equipos
   - `player_stats` - Estadísticas de jugadores
   - `standings` - Clasificaciones
   - `injuries` - Lesiones
   - `odds` - Cuotas de apuestas

2. **Esquema `sys` o `app`**: Datos del sistema
   - `model_versions` - Versiones de modelos
   - `predictions` - Predicciones generadas
   - `requests` - Requests de predicciones

3. **Esquema `ml`**: Datos procesados para ML
   - `ml_ready_games` - **Tabla principal** con features listas para entrenamiento
     - Columnas base: game_id, fecha, equipos, scores, stats base
     - Rolling features: home_ppg_last5, away_ppg_last5, home_net_rating_last10, away_net_rating_last10
     - Rest days: home_rest_days, away_rest_days
     - Injuries: home_injuries_count, away_injuries_count
     - Odds: implied_prob_home, implied_prob_away
     - Target: home_win (boolean)

**Configuración:**
- **Neon (cloud)**: Configurado en variables `NEON_*` en `.env`
- **Esquema ML**: Se crea con `scripts/init_ml_schema.py`
- **Nota**: Solo se usa Neon, no hay bases de datos locales

### Datos Procesados

El sistema de Scrapping genera datasets consolidados:
- `Scrapping/nba/data/processed/nba_full_dataset.csv`
- `Scrapping/premier_league/data/processed/premier_league_full_dataset.csv`

---

## 📋 Fases de Desarrollo

### ✅ FASE 1: Definir y crear la tabla objetivo `ml_ready_games`

**Objetivo**: Consolidar en una única tabla la fila por partido con columnas base y espacio para features.

**Scripts**:
- `scripts/create_ml_ready_games.py` - Crea la tabla y la pobla desde `espn.games`
- `scripts/verify_ml_ready_games.py` - Verifica la estructura y datos

**Estado**: ✅ Completada
- Tabla `ml.ml_ready_games` creada con 1,237 registros
- Columnas base y placeholders para features implementadas

### ✅ FASE 2: Feature Engineering Básico y Rolling Features

**Objetivo**: Calcular features temporales (últimos N partidos), rest days, injury counts, implied probs.

**Scripts**:
- `src/etl/build_features.py` - Script principal de feature engineering
- `scripts/verify_features.py` - Verificación de features calculadas
- `scripts/check_phase2.py` - Checks finales de la Fase 2

**Features implementadas**:
- ✅ Rolling features: `home_ppg_last5`, `away_ppg_last5`, `home_net_rating_last10`, `away_net_rating_last10` (100% aplicado)
- ✅ Rest days: `home_rest_days`, `away_rest_days` (99% aplicado)
- ✅ Injuries: `home_injuries_count`, `away_injuries_count` (100% aplicado)
- ✅ Implied probabilities: `implied_prob_home`, `implied_prob_away` (1% aplicado, limitado por datos disponibles)

**Estado**: ✅ Completada
- Todas las features calculadas y actualizadas en `ml.ml_ready_games`
- Script idempotente (se puede ejecutar múltiples veces)

### ✅ FASE 3: Dataset Final y Pruebas de Calidad (Data Quality)

**Objetivo**: Validar el dataset para evitar fugas de información y problemas de orden temporal.

**Scripts**:
- `src/etl/validate_data_quality.py` - Validación completa de calidad de datos
- `scripts/phase3_summary.py` - Resumen ejecutivo de la Fase 3

**Validaciones realizadas**:
- ✅ No leakage: Verificación de que ninguna feature use valores posteriores a la fecha del juego
- ✅ Nulos críticos: Verificación de que el target (`home_win`) no tenga NULLs
- ✅ Distribución del target: Verificación de balance (56.99% home wins, 43.01% away wins)
- ✅ Integridad de joins: Verificación de correspondencia con `espn.games`
- ✅ Validaciones adicionales: Rangos de valores, duplicados, etc.

**Estado**: ✅ Completada
- Dataset validado y listo para ML
- Todos los checks pasaron exitosamente

---

## 🚀 Guía de Uso Rápido

### 1. Instalación

```bash
cd ML
pip install -r requirements.txt
```

### 2. Inicializar Esquema ML y Crear Tabla Base

```bash
# Crear el esquema ML en Neon
python scripts/init_ml_schema.py

# Crear y poblar la tabla ml_ready_games (Fase 1)
python scripts/create_ml_ready_games.py

# Verificar la tabla creada
python scripts/verify_ml_ready_games.py
```

### 2.1. Feature Engineering (Fase 2)

```bash
# Calcular rolling features, rest days, injuries, odds
python src/etl/build_features.py

# Verificar features calculadas
python scripts/verify_features.py
python scripts/check_phase2.py
```

### 2.2. Validación de Calidad (Fase 3)

```bash
# Validar calidad del dataset
python src/etl/validate_data_quality.py

# Ver resumen ejecutivo
python scripts/phase3_summary.py
```

### 3. Probar Conexión a Base de Datos

```bash
# Probar conexiones a todas las bases de datos configuradas
python scripts/test_connection.py
```

### 4. Cargar Datos

```python
from src.data_loader import load_nba_data, DataLoader

# Opción 1: Función de conveniencia (carga desde CSV si existe, sino desde Neon)
df = load_nba_data(
    season_start="2023-10-01",
    season_end="2024-06-30",
    from_csv=True    # Intentar cargar desde CSV primero
)

# Opción 2: Usar DataLoader directamente
loader = DataLoader(schema="espn")  # Esquema ESPN en Neon

# Cargar partidos
games = loader.load_games(
    season_start="2023-10-01",
    season_end="2024-06-30",
    limit=1000
)

# Cargar estadísticas de equipos
team_stats = loader.load_team_stats(season="2023-24")

# Cargar clasificaciones
standings = loader.load_standings(season="2023-24")

# Cargar dataset consolidado (desde CSV o construir desde BD)
df = loader.load_consolidated_dataset(
    season_start="2023-10-01",
    season_end="2024-06-30"
)
```

### 5. Entrenar Modelo

```python
from src.training.train import train_model

model, metrics = train_model(
    data=df,
    model_type="ensemble",
    version="v1.0.0"
)

# Exportar modelo
from scripts.export_model import export_model
export_model(model, version="v1.0.0", metrics=metrics)
```

### 6. Registrar en Backend

```python
from scripts.register_model_version import register_model_version

register_model_version(
    version="v1.0.0",
    model_path="models/nba_prediction_model_v1.0.0.joblib",
    metadata=metrics,
    description="Primera versión del modelo ensemble",
    activate=True  # Activar esta versión
)
```

---

## 🔗 Referencias a Otras Carpetas

### Backend
- **Predicción en producción**: `Backend/app/services/prediction_service.py`
- **Carga de modelos**: Línea 60-66 de `prediction_service.py`
- **Modelo de versión**: `Backend/app/models/model_version.py`
- **Endpoint de predicciones**: `Backend/app/api/v1/endpoints/predictions.py`

### Scrapping
- **Datos de entrenamiento**: `Scrapping/nba/data/processed/nba_full_dataset.csv`
- **Conexión a BD**: `Scrapping/nba/utils/db.py`
- **ETL**: `Scrapping/nba/etl/transform_consolidate.py`

### Frontend
- **Consumo de predicciones**: `Frontend/src/services/predictions.service.ts`
- **Visualización**: `Frontend/src/pages/PredictionsPage.tsx`

---

## 📝 Notas Importantes

### Formato de Modelos

Los modelos deben exportarse en formato **joblib** (compatible con scikit-learn):

```python
import joblib

# Guardar modelo
joblib.dump(model, "models/nba_prediction_model_v1.0.0.joblib")

# El Backend carga así:
model = joblib.load("models/nba_prediction_model_v1.0.0.joblib")
```

### Estructura de Predicción

El modelo debe retornar un diccionario con:

```python
{
    "home_win_probability": float,      # 0.0 - 1.0
    "away_win_probability": float,      # 0.0 - 1.0
    "predicted_home_score": float,      # Puntos esperados
    "predicted_away_score": float,      # Puntos esperados
    "predicted_total": float,           # Total de puntos
    "recommended_bet": str,             # "home", "away", "none"
    "expected_value": float,            # Valor esperado
    "confidence_score": float,          # 0.0 - 1.0
    "model_version": str,               # Versión del modelo
    "prediction_timestamp": datetime,
    "features_used": dict               # Features utilizadas
}
```

### Variables de Entorno

El proyecto usa el mismo archivo `.env` que el Backend (ubicado en la raíz del proyecto `Tesis/`). Las variables incluyen:

**Base de datos Neon (cloud):**
- `NEON_DB_HOST`, `NEON_DB_PORT`, `NEON_DB_NAME`, `NEON_DB_USER`, `NEON_DB_PASSWORD`
- `NEON_DB_SSLMODE`, `NEON_DB_CHANNEL_BINDING`

**Esquemas:**
- `NBA_DB_SCHEMA` - Esquema ESPN (por defecto: `espn`)
- `DB_SCHEMA` - Esquema del sistema (por defecto: `sys`)
- `ML_DB_SCHEMA` - Esquema ML (por defecto: `ml`)

**Nota**: 
- El archivo `.env` ya está creado en la raíz del proyecto. Los scripts de ML lo leen automáticamente.
- Solo se usa Neon (cloud), no hay bases de datos locales.

---

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/

# Con cobertura
pytest tests/ --cov=src --cov-report=html
```

---

## 📈 Próximos Pasos

1. **Crear estructura de carpetas** según la recomendación ✅
2. **Implementar data_loader.py** para cargar datos desde PostgreSQL ✅
3. **Implementar feature_engineering.py** para crear features
4. **Entrenar modelos** (RandomForest, XGBoost, Ensemble)
5. **Evaluar modelos** con métricas apropiadas
6. **Exportar modelos** en formato joblib
7. **Integrar con Backend** registrando versiones

---

## 📖 Documentación Adicional

- **Backend README**: `../Backend/README.md`
- **Scrapping README**: `../Scrapping/README.md`
- **Frontend README**: `../Frontend/README.md`
- **Contexto del proyecto**: `CONTEXT.md`

---

## ⚠️ Consideraciones

- **Datos históricos**: Asegúrate de tener suficientes datos (mínimo 2-3 temporadas)
- **Features**: Las features deben estar disponibles en tiempo de predicción
- **Versionado**: Siempre versiona tus modelos antes de desplegar
- **Validación**: Valida modelos con datos de temporadas diferentes
- **Retraining**: Considera retrenar modelos periódicamente (cada temporada)

---

**Última actualización**: 2024
**Versión del documento**: 1.0.0
