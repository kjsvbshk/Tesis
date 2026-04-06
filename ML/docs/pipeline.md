# Pipeline de Predicción NBA — Extremo a Extremo

## Visión general

```
ESPN/NBA APIs → Scraping → PostgreSQL (espn) → Feature Engineering → ml.ml_ready_games
    → Entrenamiento (RF + XGBoost + Ensemble) → Validación Temporal → Calibración
    → Exportación (.joblib) → Backend (FastAPI) → Frontend (React)
```

El pipeline está diseñado para **prevenir data leakage** en cada etapa: las features solo usan datos pasados, la validación es temporal (nunca aleatoria), y la calibración se entrena sobre predicciones out-of-fold.

## 1. Recolección de datos

**Fuentes**: ESPN API (schedule, boxscores, standings, injuries), NBA.com (boxscores complementarios)

**Cobertura**: 3 temporadas NBA
- 2023-24: 1,322 partidos (regular + playoffs)
- 2024-25: 1,329 partidos (regular + playoffs)
- 2025-26: 1,244 partidos (temporada en curso hasta marzo 2026)
- **Total**: 3,895 registros en `espn.games`
- **Con boxscore**: 3,750+ juegos (96.2% de juegos jugados)
- **Mappings ESPN→NBA**: 3,755 (tras recuperación de 242 juegos faltantes)

**Tablas de origen** (schema `espn` en Neon PostgreSQL):
| Tabla | Contenido | Script principal |
|-------|-----------|-----------------|
| `espn.games` | Schedule, scores, stats básicas | `scrape_espn_schedule.py` |
| `espn.nba_player_boxscores` | Estadísticas individuales por jugador | `scrape_missing_2026_boxscores.py` |
| `espn.injuries` | Reportes de lesiones activas | `injuries_scraper.py` |
| `espn.odds` | Cuotas de apuestas (cobertura limitada) | `odds_scraper.py` |
| `espn.game_id_mapping` | Mapeo ESPN game_id → NBA Stats game_id | `fix_game_id_mapping.py` |

## 2. Limpieza y normalización

1. **Fechas corruptas**: El dataset original tenía fechas incorrectas (clustered en 2025-11-09). Se reparó con `scrape_espn_schedule.py` que obtiene fechas directamente de la ESPN API.

2. **Normalización de equipos**: `normalize_team()` en `map_odds_to_games.py` estandariza nombres (ej: "76ers" → "Philadelphia 76ers", "LA Clippers" → "Los Angeles Clippers").

3. **Resolución de IDs**: ESPN usa IDs de 9 dígitos; NBA Stats usa IDs de 8 dígitos. `espn.game_id_mapping` vincula ambos sistemas. Cobertura: 99.7% (3,755/3,765 juegos jugados). Se utilizan dos scrapers complementarios: `scrape_missing_2026_boxscores.py` (con mapping existente) y `scrape_new_boxscores.py` (sin mapping, usa CDN de NBA.com).

4. **Filtrado de datos inválidos**:
   - Juegos con score 0-0: partidos futuros o sin procesar → excluidos del entrenamiento
   - 130 juegos con score 0-0: futuros, postponed o sin datos → filtrados
   - 15 juegos con score pero sin boxscore recuperable (errores de red/API) → features calculadas sin boxscore (NaN en rolling stats)

## 3. Ingeniería de variables

**Script**: `ML/src/etl/build_features.py`

**21 features** organizadas en:
- **11 diferenciales**: `home_value - away_value` (ppg, ratings, rest days, injuries, pace, reb, ast, tov, win rate)
- **10 individuales**: valores absolutos (ppg, rest days, b2b, injuries, win rate) por equipo

**Prevención de data leakage**:
```python
# Todas las rolling features usan shift(1):
feature = series.shift(1).rolling(window).mean()
# Esto garantiza que el juego N solo usa datos de juegos 1..N-1
```

**Fórmulas clave**:
```
Posesiones = FGA + 0.44 × FTA - OReb + TOV
Off Rating = (Puntos / Posesiones) × 100
Def Rating = (Puntos rival / Posesiones) × 100
Net Rating = Off Rating - Def Rating
```

**Tabla de salida**: `ml.ml_ready_games` (3,895 registros; 3,875 con features completas, 20 sin features por ser primeros de temporada)

## 4. Entrenamiento

**Script**: `ML/src/training/train.py`

**Arquitectura del Ensemble (Stacking)**:

```
Nivel 1 (Modelos base):
  RandomForest → P(home_win) calibrada con Isotonic Regression
  XGBoost      → score_diff (home_score_pred - away_score_pred)

Nivel 2 (Meta-learner):
  LogisticRegression([rf_proba, score_diff]) → P_final(home_win)

Calibración final: Isotonic Regression sobre predicciones OOF
```

**RandomForest** (`ML/src/models/random_forest.py`):
- 300 estimadores, max_depth=8, class_weight="balanced"
- Pipeline: SimpleImputer(median) → StandardScaler → CalibratedClassifierCV(isotonic, cv=5)

**XGBoost** (`ML/src/models/xgboost_model.py`):
- Doble regresor: predice home_score y away_score independientemente
- 200 estimadores, max_depth=5, learning_rate=0.05
- Scores clipped a [70, 160] (rango realista NBA)

**Ensemble** (`ML/src/models/ensemble.py`):
- Out-of-Fold (OOF) Stacking con 5 folds temporales
- Meta-learner: LogisticRegression(C=0.5)
- Calibración final: IsotonicRegression sobre predicciones OOF
- Retrain de base models sobre dataset completo para producción

## 5. Validación temporal

**Script**: `ML/src/evaluation/validation.py`

**Regla obligatoria**: Nunca se usa validación aleatoria (train_test_split con shuffle). Todos los splits son temporales.

**Split principal**: 80% train / 20% test, ordenado cronológicamente.
- Train: juegos más antiguos
- Test: juegos más recientes (753 partidos en evaluación v2)

**Expanding Window Cross-Validation** (5 folds):
```
Split 1: Train [  0% → 40%]  Val [40% → 52%]
Split 2: Train [  0% → 52%]  Val [52% → 64%]
Split 3: Train [  0% → 64%]  Val [64% → 76%]
Split 4: Train [  0% → 76%]  Val [76% → 88%]
Split 5: Train [  0% → 88%]  Val [88% → 100%]
```

El set de entrenamiento siempre empieza desde el principio y se EXPANDE. No hay datos futuros en ningún fold de entrenamiento.

## 6. Calibración

La calibración es crucial para apuestas: las probabilidades predichas deben reflejar frecuencias reales.

**Estrategia de calibración en dos niveles**:

1. **RandomForest**: `CalibratedClassifierCV` con método isotónico y cv=5 interno.
2. **Ensemble**: Isotonic Regression entrenada sobre predicciones OOF (out-of-fold), no sobre predicciones del train set. Esto previene sobreajuste en la calibración.

**Resultado**: ECE = 0.0834 en evaluación v2 (objetivo < 0.05). La calibración se degrada en datos más recientes (test set dic 2025 - mar 2026), sugiriendo necesidad de re-entrenamiento periódico. En el test set original, ECE era 0.0363.

## 7. Exportación

**Formato**: `.joblib` (modelo serializado) + `.json` (metadata con métricas)

**Rutas**:
```
ML/models/nba_prediction_model_v1.6.0.joblib  → modelo
ML/models/metadata/v1.6.0_metadata.json        → métricas + features
```

**Metadata incluye**: versión, tipo de modelo, lista de features, timestamp, todas las métricas de evaluación.

## 8. Integración con Backend y Frontend

**Backend** (`Backend/`):
- FastAPI carga el modelo `.joblib` al iniciar
- Endpoint `/predictions/` genera predicciones en tiempo real
- Cache de 5 minutos para evitar recálculos
- Predicciones incluyen: P(home_win), scores predichos, recommended_bet, EV

**Frontend** (`Frontend/`):
- React 19 + TypeScript muestra predicciones al usuario
- Interfaz de apuestas virtuales con bankroll simulado

## 9. Monitoreo y versionado

- **11 versiones** entrenadas (v1.0.0 → v1.6.0) con mejoras incrementales
- Registro en `sys.model_versions` (solo una versión activa a la vez)
- `ML/scripts/compare_models.py`: compara métricas entre versiones
- `ML/scripts/register_model_version.py`: activa/desactiva versiones en producción
- **Versión oficial**: v1.6.0 (congelada como baseline de tesis)
