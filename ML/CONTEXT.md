# Contexto del Proyecto - Resumen Ejecutivo

Este documento proporciona un resumen rápido del contexto del proyecto para entender cómo se integra la carpeta ML.

## 🎯 Objetivo del Proyecto

Sistema completo de **predicciones y apuestas virtuales** para partidos de la NBA usando Machine Learning.

## 🏗️ Componentes del Sistema

### 1. Scrapping (`../Scrapping/`)
**Función**: Extracción automatizada de datos de ESPN

**Datos extraídos**:
- Partidos y resultados (boxscores)
- Estadísticas de jugadores
- Estadísticas de equipos
- Clasificaciones (standings)
- Lesiones
- Cuotas de apuestas

**Output**: Datos almacenados en PostgreSQL (esquema `espn`) y archivos CSV procesados

**Ubicación de datos procesados**:
- `Scrapping/nba/data/processed/nba_full_dataset.csv`

---

### 2. ML (`./ML/`) ← **ESTA CARPETA**
**Función**: Entrenamiento y gestión de modelos de Machine Learning

**Responsabilidades**:
- Cargar datos históricos
- Feature engineering
- Entrenar modelos (RandomForest, XGBoost, Ensemble)
- Evaluar modelos
- Exportar modelos para producción
- Gestionar versiones de modelos

**Output**: Modelos entrenados en formato `.joblib` que se usan en Backend

---

### 3. Backend (`../Backend/`)
**Función**: API REST que usa los modelos ML para generar predicciones en tiempo real

**Tecnologías**: FastAPI, PostgreSQL, SQLAlchemy

**Componentes clave**:
- `app/services/prediction_service.py` - Carga modelos y genera predicciones
- `app/models/model_version.py` - Gestiona versiones de modelos
- `app/api/v1/endpoints/predictions.py` - Endpoints de API

**Cómo carga modelos**:
```python
# Backend busca modelos en:
Backend/ml/models/nba_prediction_model_{version}.joblib
```

**Base de datos**:
- Esquema `espn`: Datos de partidos (desde Scrapping)
- Esquema `app`: Datos del sistema (usuarios, apuestas, predicciones, versiones de modelos)

---

### 4. Frontend (`../Frontend/`)
**Función**: Interfaz web para usuarios

**Tecnologías**: React, TypeScript, Vite, Tailwind CSS

**Funcionalidades**:
- Ver partidos disponibles
- Solicitar predicciones
- Hacer apuestas virtuales
- Ver historial de apuestas

---

## 🔄 Flujo Completo del Sistema

```
┌─────────────┐
│  Scrapping  │ → Extrae datos de ESPN
└──────┬──────┘
       │
       ↓ Datos históricos
┌─────────────┐
│     ML      │ → Entrena modelos con datos históricos
└──────┬──────┘
       │
       ↓ Modelos entrenados (.joblib)
┌─────────────┐
│   Backend   │ → Carga modelos y genera predicciones en tiempo real
└──────┬──────┘
       │
       ↓ API REST
┌─────────────┐
│  Frontend   │ → Muestra predicciones y permite apuestas
└─────────────┘
```

---

## 📊 Modelos de Machine Learning

### RandomForest
- **Tipo**: Clasificación
- **Predice**: ¿Quién ganará? (home/away)
- **Output**: Probabilidad de victoria

### XGBoost
- **Tipo**: Regresión
- **Predice**: ¿Cuántos puntos anotará cada equipo?
- **Output**: Puntuación esperada

### Stacking Ensemble
- **Tipo**: Meta-modelo
- **Combina**: RandomForest + XGBoost
- **Output**: Predicción final con mayor confianza

---

## 🗄️ Base de Datos

**Proveedor**: Neon PostgreSQL

**Esquemas**:

1. **`espn`** - Datos de partidos (desde Scrapping)
   - `games` - Partidos y resultados
   - `team_stats` - Estadísticas de equipos
   - `player_stats` - Estadísticas de jugadores
   - `standings` - Clasificaciones
   - `injuries` - Lesiones
   - `odds` - Cuotas de apuestas

2. **`app`** - Datos del sistema
   - `users` - Usuarios
   - `games` - Partidos (referencia a espn.games)
   - `bets` - Apuestas virtuales
   - `predictions` - Predicciones generadas
   - `model_versions` - Versiones de modelos ML
   - `requests` - Requests de predicciones

---

## 🔑 Conceptos Clave

### Versionado de Modelos
- Cada modelo tiene una versión (e.g., `v1.0.0`)
- Solo una versión puede estar activa (`is_active=True`)
- Los modelos se almacenan en `Backend/ml/models/`
- Las versiones se registran en `app.model_versions`

### Predicciones
- Se generan en tiempo real cuando un usuario solicita una predicción
- Se guardan en `app.predictions` con telemetría (latencia, versión del modelo)
- Se cachean por 5 minutos (stale-while-revalidate)

### Apuestas Virtuales
- Los usuarios usan créditos virtuales (no dinero real)
- Las apuestas se basan en las predicciones
- El sistema calcula ganancias según probabilidades

---

## 📁 Estructura de Archivos Clave

```
Tesis/
├── Backend/
│   ├── app/
│   │   ├── services/
│   │   │   └── prediction_service.py    # Usa modelos ML
│   │   ├── models/
│   │   │   └── model_version.py         # Versionado
│   │   └── api/v1/endpoints/
│   │       └── predictions.py           # Endpoints API
│   └── ml/
│       └── models/                      # Modelos entrenados (desde ML/)
│
├── Frontend/
│   └── src/
│       ├── services/
│       │   └── predictions.service.ts   # Consume API
│       └── pages/
│           └── PredictionsPage.tsx      # UI
│
├── Scrapping/
│   └── nba/
│       ├── data/processed/
│       │   └── nba_full_dataset.csv     # Datos para entrenar
│       └── load_data.py                 # Carga a PostgreSQL
│
└── ML/                                  # ← ESTA CARPETA
    ├── src/                             # Código de entrenamiento
    ├── models/                          # Modelos entrenados
    └── notebooks/                       # Análisis exploratorio
```

---

## 🚀 Próximos Pasos para ML

1. **Setup inicial**
   - Crear estructura de carpetas
   - Instalar dependencias (`pip install -r requirements.txt`)

2. **Cargar datos**
   - Conectar a PostgreSQL
   - Cargar datos históricos de `espn` schema
   - O usar CSV procesado de Scrapping

3. **Feature engineering**
   - Crear features relevantes
   - Normalizar datos
   - Manejar valores faltantes

4. **Entrenar modelos**
   - RandomForest para clasificación
   - XGBoost para regresión
   - Ensemble para combinar ambos

5. **Evaluar modelos**
   - Métricas de clasificación (accuracy, precision, recall)
   - Métricas de regresión (MAE, RMSE)
   - Validación cruzada

6. **Exportar modelos**
   - Guardar en formato `.joblib`
   - Copiar a `Backend/ml/models/`
   - Registrar versión en BD

---

## 📚 Referencias Rápidas

- **Backend README**: `../Backend/README.md`
- **Scrapping README**: `../Scrapping/README.md`
- **Frontend README**: `../Frontend/README.md`
- **ML README**: `./README.md` (más detallado)

---

**Última actualización**: 2024

