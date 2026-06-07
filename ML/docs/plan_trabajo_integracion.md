# Plan de Trabajo — Integración ML en Backend y Frontend

## Contexto

El modelo v2.0.0 (Ensemble RF+XGBoost+MarginModel+TotalModel) está entrenado y exportado
como `nba_prediction_model_v2.0.0.joblib`. Sin embargo:

- El backend usa `_generate_dummy_prediction()` — **nunca ha corrido inferencia real**
- El backend no puede construir el vector de features que el modelo espera
- El frontend consume los campos correctos pero nunca ha visto datos reales del modelo
- El flujo de deploy de modelos (train → copiar → registrar → activar) no existe como proceso

Este plan define exactamente qué implementar, en qué orden, y cómo verificar cada paso.

---

## Entregable 1: Feature Service en Backend (`Backend/app/services/feature_service.py`)

### Objetivo
Proveer al `PredictionService` el vector de 33 features que el modelo espera, consultando
`ml.ml_ready_games` (la tabla ya tiene las features precomputadas por el pipeline ML).

### Lógica
El joblib fue entrenado sobre `ml.ml_ready_games`. Para predecir un partido, el backend
consulta esa misma tabla por `game_id` y extrae las 33 columnas de features.
No se duplica la lógica de feature engineering — se reutiliza el output del pipeline ML.

### Implementación

**Archivo**: `Backend/app/services/feature_service.py`

**Clase**: `FeatureService`

**Métodos**:

```python
class FeatureService:
    FEATURE_COLS = [
        # 18 diferenciales
        "ppg_diff", "net_rating_diff_rolling", "rest_days_diff", "injuries_diff",
        "pace_diff", "off_rating_diff", "def_rating_diff", "reb_rolling_diff",
        "ast_rolling_diff", "tov_rolling_diff", "win_rate_diff",
        "efg_pct_diff", "tov_rate_diff", "oreb_pct_diff", "dreb_pct_diff",
        "elo_diff", "streak_diff", "home_away_split_diff",
        # 15 individuales
        "home_ppg_last5", "away_ppg_last5", "home_rest_days", "away_rest_days",
        "home_b2b", "away_b2b", "home_injuries_count", "away_injuries_count",
        "home_win_rate_last10", "away_win_rate_last10",
        "home_elo", "away_elo", "home_streak", "away_streak", "h2h_home_advantage",
    ]

    def get_features_for_game(self, game_id: int) -> np.ndarray | None:
        """
        Consulta ml.ml_ready_games por game_id y retorna array de shape (1, 33).
        Retorna None si el juego no tiene features disponibles aún.
        """

    def get_feature_dict_for_game(self, game_id: int) -> dict | None:
        """
        Igual que get_features_for_game pero retorna {feature_name: value}
        para incluir en features_used de la respuesta.
        """
```

**Conexión a DB**:
- Usar la misma conexión de DB del `PredictionService` (ya conectada a Neon)
- Schema ML en variable de entorno `ML_SCHEMA` (default: `ml`)
- Query: `SELECT {feature_cols} FROM {ml_schema}.ml_ready_games WHERE game_id = :game_id`

**Manejo de features faltantes**:
- Si el juego existe pero hay NULLs en features: rellenar con `0.0` (mismo comportamiento que `SimpleImputer` del pipeline)
- Si el juego no existe en `ml_ready_games`: retornar `None` (el caller cae a dummy)
- Loggear un WARNING si más de 5 features son NULL (señal de datos incompletos)

### Verificación

```bash
# Desde Backend/
python -c "
from app.services.feature_service import FeatureService
import os
# Usar un game_id conocido de ml_ready_games
fs = FeatureService(db_session)
X = fs.get_features_for_game(game_id=401585123)
print(X.shape)  # Esperado: (1, 33)
print('NULLs:', sum(np.isnan(X[0])))  # Esperado: 0 o muy pocos
"
```

**Criterios de éxito**:
- [ ] `get_features_for_game()` retorna array shape `(1, 33)` para game_id conocido
- [ ] Retorna `None` para game_id inexistente (sin excepción)
- [ ] Las columnas están en el mismo orden que `FEATURE_COLS` de `train.py`
- [ ] NULLs se rellenan con 0.0, no se propagan
- [ ] No hay import circular con otros servicios del backend

---

## Entregable 2: Implementar `_predict_with_model()` real (`Backend/app/services/prediction_service.py`)

### Objetivo
Reemplazar la llamada a `_generate_dummy_prediction()` con inferencia real usando los tres
sub-modelos del ensemble: clasificador de victoria, modelo de margen, modelo de total.

### Arquitectura del joblib

El archivo `nba_prediction_model_{version}.joblib` es un objeto `NBAEnsemble` que contiene:
- `ensemble.rf` → `NBARandomForest` → `predict_proba(X)` → `P(home_win)`
- `ensemble.xgb` → `NBAXGBoost` → predice scores individuales
- `ensemble.margin_model` → `NBAMarginModel` → `predict(X)` → point_diff
- `ensemble.total_model` → `NBATotalModel` → `predict(X)` → total_points
- `ensemble.predict_proba(X)` → `P_final(home_win)` (output del meta-learner + calibración)

### Implementación

**Archivo a modificar**: `Backend/app/services/prediction_service.py` (línea 271)

**Cambios en `__init__`**:
```python
from app.services.feature_service import FeatureService
self.feature_service = FeatureService(db)
```

**Reemplazar `_predict_with_model()`**:
```python
async def _predict_with_model(self, game, home_team, away_team) -> dict:
    game_id = game.get("id") or game.get("game_id")

    # 1. Construir features
    X = self.feature_service.get_features_for_game(game_id)
    if X is None:
        print(f"⚠️  No features for game {game_id}, falling back to dummy")
        return await self._generate_dummy_prediction(game, home_team, away_team)

    # 2. Inferencia
    home_win_prob = float(self.model.predict_proba(X)[0, 1])
    predicted_margin = float(self.model.margin_model.predict(X)[0])
    predicted_total = float(self.model.total_model.predict(X)[0])

    # 3. Derivar scores individuales desde margen y total
    # total = home + away  →  home = (total + margin) / 2
    predicted_home_score = (predicted_total + predicted_margin) / 2
    predicted_away_score = (predicted_total - predicted_margin) / 2

    # 4. EV y recomendación (igual que antes)
    away_win_prob = 1.0 - home_win_prob
    ...

    # 5. Features usadas (para trazabilidad)
    feature_dict = self.feature_service.get_feature_dict_for_game(game_id)

    return {
        "home_win_probability": round(home_win_prob, 4),
        "away_win_probability": round(away_win_prob, 4),
        "predicted_home_score": round(predicted_home_score, 1),
        "predicted_away_score": round(predicted_away_score, 1),
        "predicted_total": round(predicted_total, 1),
        "predicted_margin": round(predicted_margin, 1),
        "recommended_bet": ...,
        "expected_value": ...,
        "confidence_score": round(max(home_win_prob, away_win_prob), 4),
        "model_version": self.model_version_obj.version,
        "prediction_timestamp": datetime.utcnow(),
        "features_used": feature_dict,
    }
```

**Funciones a reusar**:
- `FeatureService.get_features_for_game()` (E1)
- `_generate_dummy_prediction()` como fallback si features no disponibles

### Verificación

```bash
# Llamar al endpoint con game_id que existe en ml_ready_games
curl -X POST "http://localhost:8000/api/v1/predict/" \
  -H "Content-Type: application/json" \
  -d '{"game_id": 401585123}'
```

**Criterios de éxito**:
- [ ] La respuesta incluye `home_win_probability` entre 0.3-0.8 (rango realista, no dummy ~0.55)
- [ ] `predicted_margin` aparece en la respuesta (campo nuevo)
- [ ] `predicted_total` está entre 200-260 (rango NBA realista)
- [ ] `features_used` contiene los nombres y valores de las 33 features (no solo home_court_advantage)
- [ ] `model_version` coincide con la versión activa en DB
- [ ] Si game_id no tiene features, usa dummy sin crashear
- [ ] Latencia < 500ms para un game_id (carga + features + inferencia)

---

## Entregable 3: Configuración de Rutas de Modelo (`Backend/.env` + `prediction_service.py`)

### Problema actual
```python
model_path = os.path.join("ml", "models", f"nba_prediction_model_{version}.joblib")
```
Ruta relativa al CWD — si el backend corre desde un directorio diferente, falla silenciosamente.

### Implementación

**Agregar a `Backend/.env`**:
```
MODEL_DIR=/ruta/absoluta/a/ML/models
```

**Agregar a `Backend/app/core/config.py`** (o donde estén las settings):
```python
MODEL_DIR: str = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(__file__), "../../ml/models"))
```

**Modificar `load_model()` en `prediction_service.py`**:
```python
from app.core.config import settings
model_path = os.path.join(settings.MODEL_DIR, f"nba_prediction_model_{version}.joblib")
```

**Agregar a `.env.example`**:
```
MODEL_DIR=../ML/models  # Ruta relativa al directorio Backend/, o absoluta
```

### Verificación

```bash
# Iniciar backend desde directorio incorrecto (debería igual encontrar el modelo)
cd /tmp && uvicorn app.main:app --app-dir /ruta/a/Backend
# GET /predict/model/status debe retornar model_loaded: true
```

**Criterios de éxito**:
- [ ] `MODEL_DIR` se lee desde `.env` o variable de entorno
- [ ] La carga del modelo funciona sin importar el CWD del proceso
- [ ] Hay un valor default sensato si `MODEL_DIR` no está definido
- [ ] `.env.example` documenta la variable

---

## Entregable 4: Agregar `predicted_margin` al Schema

### Objetivo
El modelo de margen ya genera `predicted_margin`. Exponerlo en la API y el frontend.

### Backend — `Backend/app/schemas/prediction.py`

Agregar campo en `PredictionResponse`:
```python
predicted_margin: Optional[float] = None  # point_diff = home_score - away_score
```

### Verificación backend

```bash
python -c "
from app.schemas.prediction import PredictionResponse
import inspect
fields = PredictionResponse.model_fields
assert 'predicted_margin' in fields
print('predicted_margin field OK')
"
```

**Criterios de éxito**:
- [ ] `predicted_margin` existe en `PredictionResponse` como `Optional[float]`
- [ ] Todos los endpoints que retornan `PredictionResponse` incluyen el campo
- [ ] Valor positivo = predicción de victoria local, negativo = derrota

---

## Entregable 5: Endpoints de Versioning (`Backend/app/api/v1/endpoints/predictions.py`)

### Objetivo
Permitir listar versiones disponibles y activar una desde la API (sin tocar la DB directamente).

### Endpoints nuevos

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/predict/model/versions` | Lista todas las versiones registradas con métricas |
| `POST` | `/predict/model/versions/{version}/activate` | Activa una versión (desactiva la anterior) |

**Response de GET `/versions`**:
```json
[
  {
    "version": "v2.0.0",
    "is_active": true,
    "description": "Ensemble con 33 features, MarginModel y TotalModel",
    "created_at": "2026-03-15T...",
    "metrics": { "log_loss": 0.6855, "roc_auc": 0.6462, "ece": 0.0925 }
  }
]
```

**POST `/versions/{version}/activate`**:
- Actualiza `is_active` en DB
- Llama `self.prediction_service.load_model()` para recargar en memoria
- Retorna la versión ahora activa

**Modificar `get_model_status()`** (línea 333 de prediction_service.py) para retornar datos reales:
```python
async def get_model_status(self) -> dict:
    return {
        "model_loaded": self.model is not None,
        "model_version": self.model_version_obj.version if self.model_version_obj else None,
        "model_type": type(self.model).__name__ if self.model else "Dummy",
        "trained_at": self.model_version_obj.created_at.isoformat() if self.model_version_obj else None,
        "metrics": self.model_version_obj.model_metadata if self.model_version_obj else {},
        "status": "ready" if self.model else "dummy_mode",
        "using_real_predictions": self.model is not None,
    }
```

### Verificación

```bash
curl http://localhost:8000/api/v1/predict/model/versions
# Esperado: lista de versiones con is_active=true en exactamente una

curl -X POST http://localhost:8000/api/v1/predict/model/versions/v2.0.0/activate
# Esperado: {"version": "v2.0.0", "is_active": true, ...}
```

**Criterios de éxito**:
- [ ] GET versions retorna todas las versiones registradas (al menos v2.0.0)
- [ ] POST activate cambia el modelo en memoria sin reiniciar el proceso
- [ ] `get_model_status()` retorna métricas reales del JSON de metadata, no valores hardcodeados
- [ ] Solo una versión puede estar activa al mismo tiempo
- [ ] Activar una versión cuyo .joblib no existe retorna error claro (404 con mensaje)

---

## Entregable 6: Script de Deploy de Modelo (`ML/scripts/deploy_model.py`)

### Objetivo
Un solo comando que cubre el flujo completo post-entrenamiento:
1. Copia el .joblib al directorio del backend
2. Registra la versión en la DB
3. La activa opcionalmente

### Implementación

**Archivo**: `ML/scripts/deploy_model.py`

```bash
# Uso:
python -m scripts.deploy_model --version v2.0.0 --activate
python -m scripts.deploy_model --version v2.0.0  # Solo registra, no activa
```

**Pasos internos**:
1. Verificar que `ML/models/nba_prediction_model_{version}.joblib` existe
2. Leer `ML/models/metadata/{version}_metadata.json`
3. Determinar `BACKEND_MODEL_DIR` desde `.env` del backend o argumento `--backend-dir`
4. Copiar el .joblib a `BACKEND_MODEL_DIR/`
5. Llamar `register_model_version(version, activate=args.activate)` (reusar lógica existente)
6. Imprimir confirmación con métricas clave

**Reusar**:
- `ML/scripts/register_model_version.py`: `register_model_version()`, `activate_version()`

**Nuevo (inline, sin helper separado)**:
- Lógica de copy + verificación de destino

### Verificación

```bash
python -m scripts.deploy_model --version v2.0.0 --activate
```

Output esperado:
```
✅ Copiado: ML/models/nba_prediction_model_v2.0.0.joblib → Backend/ml/models/
✅ Registrado en sys.model_versions (id=N)
✅ Activado: v2.0.0 (anterior: v1.6.0 desactivada)
   log_loss=0.6855 | roc_auc=0.6462 | ece=0.0925
```

**Criterios de éxito**:
- [ ] El .joblib aparece en el directorio del backend después de ejecutar
- [ ] La versión aparece en `sys.model_versions` con `is_active=TRUE` si se usó `--activate`
- [ ] Si el .joblib fuente no existe, falla con mensaje claro antes de cualquier operación de DB
- [ ] Si el destino ya tiene el archivo, sobreescribe con WARNING visible
- [ ] `--help` describe todos los argumentos

---

## Entregable 7: Frontend — Mostrar `predicted_margin` (`Frontend/src/`)

### Objetivo
Mostrar el margen predicho en los lugares donde se muestran predicciones.

### Cambios

**`Frontend/src/services/predictions.service.ts`** — agregar campo:
```typescript
export interface PredictionResponse {
  // ... campos existentes ...
  predicted_margin?: number  // positivo = victoria local, negativo = derrota
}
```

**`Frontend/src/pages/PredictionsPage.tsx`** — agregar StatCard:
```tsx
<StatCard
  label="PREDICTED MARGIN"
  value={`${prediction.predicted_margin > 0 ? '+' : ''}${prediction.predicted_margin?.toFixed(1)}`}
  subtitle={prediction.predicted_margin > 0 ? 'Home favored' : 'Away favored'}
/>
```

**`Frontend/src/components/MatchCard.tsx`** — agregar badge de margen (opcional, si hay espacio):
```tsx
{aiPredictedMargin !== undefined && (
  <span className="margin-badge">
    {aiPredictedMargin > 0 ? `+${aiPredictedMargin.toFixed(0)}` : aiPredictedMargin.toFixed(0)}
  </span>
)}
```

### Verificación

- [ ] `PredictionsPage` muestra el margen con signo (`+5.2` o `-3.1`)
- [ ] El signo está coloreado (verde = local gana, rojo = visitante gana)
- [ ] Si `predicted_margin` es `undefined` (versiones antiguas), el StatCard no aparece
- [ ] No hay TypeScript errors en compilación

---

## Entregable 8: Frontend — Panel de Versión de Modelo (`Frontend/src/pages/PredictionsPage.tsx`)

### Objetivo
Mostrar qué versión del modelo generó la predicción y cuándo fue entrenado.
Reemplazar los valores dummy de `get_model_status()`.

### Cambios en `PredictionsPage.tsx`

Agregar sección de modelo info (abajo de las predicciones o en un modal/tooltip):
```tsx
<ModelInfo
  version={prediction.model_version}       // "v2.0.0"
  trainedAt={modelStatus?.trained_at}      // ISO date
  metrics={modelStatus?.metrics}           // {log_loss, roc_auc, ece}
  isRealPrediction={modelStatus?.using_real_predictions}
/>
```

**Regla**: si `using_real_predictions === false`, mostrar un badge visible "SIMULADO"
para que el usuario sepa que los datos son dummy.

### Verificación

- [ ] La versión del modelo se muestra (ej: "v2.0.0")
- [ ] Si el backend está en modo dummy, se muestra badge "SIMULADO" visible
- [ ] No hay crash si `modelStatus` es null (backend sin conexión)

---

## Orden de Ejecución

```
Fase 1: Backend (prerrequisito para todo)
  1. E3: Configurar MODEL_DIR en .env           ← sin dependencias, rápido
  2. E1: Feature Service                         ← requiere acceso a ml.ml_ready_games
  3. E4: Agregar predicted_margin al schema      ← sin dependencias, rápido
  4. E2: _predict_with_model() real              ← depende de E1 y E3
  5. E5: Endpoints de versioning                 ← depende de E2 (model_status real)

Fase 2: ML Workflow
  6. E6: Script deploy_model.py                  ← independiente

Fase 3: Frontend
  7. E7: Mostrar predicted_margin               ← depende de E4 (schema)
  8. E8: Panel de versión                       ← depende de E5 (model_status real)

Dependencias:
  E1 → E2 → E5 (feature service → inferencia real → versioning endpoints)
  E3 → E2 (path config → carga de modelo)
  E4 → E7 (schema → frontend)
  E5 → E8 (model_status real → frontend panel)
```

---

## Resumen de Archivos

### Archivos nuevos a crear
| Archivo | Tipo | Entregable |
|---------|------|-----------|
| `Backend/app/services/feature_service.py` | Servicio Python | E1 |
| `ML/scripts/deploy_model.py` | Script Python | E6 |

### Archivos existentes a modificar
| Archivo | Cambio | Entregable |
|---------|--------|-----------|
| `Backend/app/services/prediction_service.py` | `_predict_with_model()` real + `get_model_status()` real | E2, E5 |
| `Backend/app/schemas/prediction.py` | Agregar `predicted_margin` | E4 |
| `Backend/app/api/v1/endpoints/predictions.py` | Endpoints de versioning | E5 |
| `Backend/app/core/config.py` | Agregar `MODEL_DIR` | E3 |
| `Backend/.env` / `.env.example` | Variable `MODEL_DIR` | E3 |
| `Frontend/src/services/predictions.service.ts` | Agregar `predicted_margin` a interface | E7 |
| `Frontend/src/pages/PredictionsPage.tsx` | StatCard de margen + panel de versión | E7, E8 |
| `Frontend/src/components/MatchCard.tsx` | Badge de margen opcional | E7 |

### Archivos existentes que se REUSAN sin modificar
| Archivo | Reutilizado para |
|---------|-----------------|
| `ML/scripts/register_model_version.py` | Base para `deploy_model.py` (E6) |
| `ML/src/models/ensemble.py` | API de inferencia en E2 |
| `Backend/app/models/model_version.py` | ORM para versioning en E5 |

---

## Notas de Implementación

### Sobre el joblib y los sub-modelos
`NBAEnsemble` tiene `self.margin_model` y `self.total_model` como atributos. Después de
`model = joblib.load(path)`, están accesibles directamente:
```python
model.predict_proba(X)          # → home_win prob
model.margin_model.predict(X)   # → point_diff
model.total_model.predict(X)    # → total_points
```

### Sobre ml.ml_ready_games para juegos futuros
La tabla `ml_ready_games` contiene features precomputadas de juegos históricos.
Para juegos futuros (status="scheduled"), puede que no hayan corrido los scrapers aún.
**Solución provisional**: si `get_features_for_game()` retorna `None`, caer a dummy
y loggear el game_id para monitoreo.

### Sobre v2.0.0 y criterios de aceptación
v2.0.0 **no pasa todos los criterios**: log_loss=0.6855 (umbral 0.68), ECE=0.0925 (umbral 0.05).
La integración debe funcionar con cualquier versión — no bloquear el deploy por criterios.
Los criterios son para decidir qué versión activar en producción, no para ejecutar la integración.
