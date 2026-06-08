# Plan de Trabajo — Consolidación v1.6.0 y Documentación de Tesis

## Contexto

El modelo v1.6.0 (Ensemble RF+XGBoost) está entrenado y pasa todos los criterios de aceptación tras corregir data leakage. Sin embargo, para que el documento de tesis sea riguroso, faltan:
- Comparaciones contra baselines simples
- Backtesting de rentabilidad con métricas económicas completas
- Visualizaciones de calibración
- Documentación formal de pipeline, features, limitaciones y hoja de ruta

Este plan define exactamente qué se debe implementar, en qué orden, y cómo verificar cada paso.

---

## Entregable 1: Script de Baselines (`ML/scripts/baselines.py`)

### Objetivo
Demostrar que el ensemble v1.6.0 supera enfoques simples. Sin esta comparación, no hay evidencia de que el modelo aporte valor.

### Baselines a implementar

| # | Baseline | Lógica | Métrica esperada |
|---|----------|--------|-----------------|
| 1 | **Siempre local** | P(home_win) = 1.0 para todos | Accuracy ~57% (home win rate histórico) |
| 2 | **Moneda al aire** | P(home_win) = 0.5 para todos | Accuracy ~50%, Log Loss = 0.693 |
| 3 | **Home win rate fijo** | P(home_win) = 0.57 (proporción histórica) | Brier baseline |
| 4 | **Logistic Regression** | LR entrenada con las mismas 21 features | Baseline ML mínimo |
| 5 | **Random Forest solo** | RF sin ensemble, sin XGBoost | Baseline ML intermedio |
| 6 | **XGBoost solo** | XGB clasificador (no regresor de scores) | Baseline ML intermedio |
| 7 | **Ensemble v1.6.0** | Modelo oficial | Debe superar todos los anteriores |

### Implementación

**Archivo**: `ML/scripts/baselines.py`

**Pasos del script**:
1. Cargar datos de `ml.ml_ready_games` (reusar `load_ml_ready_games()` de `train.py`)
2. Aplicar `build_feature_matrix()` con las mismas 21 features
3. Hacer `temporal_train_test_split()` con `test_size=0.20` (misma partición que v1.6.0)
4. Para cada baseline:
   - **Heurísticas** (1-3): generar array de probabilidades constantes, evaluar contra y_test
   - **LR**: entrenar `LogisticRegression(C=0.5, max_iter=1000)` con pipeline `SimpleImputer → StandardScaler → LR`
   - **RF solo**: usar `NBARandomForest` existente (`ML/src/models/random_forest.py`)
   - **XGB clasificador**: crear `XGBClassifier` con los mismos hiperparámetros que el regresor pero como clasificación binaria
   - **Ensemble**: cargar `nba_prediction_model_v1.6.0.joblib`
5. Calcular para cada uno: Log Loss, Brier Score, ROC-AUC, ECE, Accuracy
6. Imprimir tabla comparativa formateada
7. Guardar resultados en `ML/reports/baselines_comparison.json`

**Funciones a reusar** (NO crear nuevas):
- `ML/src/training/train.py`: `load_ml_ready_games()`, `build_feature_matrix()`
- `ML/src/evaluation/validation.py`: `temporal_train_test_split()`
- `ML/src/evaluation/metrics.py`: `evaluate_classifier()`
- `ML/src/models/random_forest.py`: `NBARandomForest`

**Funciones nuevas requeridas**:
- Ninguna función de utilidad nueva. El XGB clasificador se crea inline con `XGBClassifier` + `SimpleImputer` + pipeline de sklearn.

### Verificación

```bash
python -m scripts.baselines
```

**Criterios de éxito**:
- [ ] Las 7 filas aparecen en la tabla de salida
- [ ] "Siempre local" tiene Accuracy ~57% y Log Loss alto (~0.68+)
- [ ] "Moneda al aire" tiene Log Loss ≈ 0.693 (ln(2))
- [ ] LR tiene métricas inferiores al Ensemble
- [ ] RF solo tiene métricas inferiores o similares al Ensemble
- [ ] Ensemble v1.6.0 tiene el mejor (o cercano al mejor) Log Loss
- [ ] El JSON de salida se genera en `ML/reports/baselines_comparison.json`
- [ ] No hay errores de importación ni de datos faltantes
- [ ] La partición temporal usa EXACTAMENTE el mismo split que v1.6.0 (verificar fechas de corte)

---

## Entregable 2: Backtesting de Rentabilidad (`ML/scripts/backtesting.py`)

### Objetivo
Mostrar si el modelo puede generar rentabilidad simulada, o al menos documentar honestamente que accuracy no implica profit.

### Implementación

**Archivo**: `ML/scripts/backtesting.py`

**Dependencia**: Requiere odds históricas. Actualmente solo ~1% de juegos tienen `implied_prob_home`. Si no hay odds suficientes, el script debe:
1. Simular odds de mercado basadas en la probabilidad implícita del home win rate histórico (~57%)
2. Documentar claramente que son odds simuladas, no reales

**Estrategias de apuesta a implementar**:

| # | Estrategia | Lógica |
|---|-----------|--------|
| 1 | **Stake fijo** | Apuesta $1 en cada juego donde EV > 0.05 y P > 0.55 (regla actual del model spec §5.2) |
| 2 | **Kelly fraccional (25%)** | Apuesta = 0.25 × f*, donde f* = (p × o - 1) / (o - 1) |
| 3 | **Flat en todos** | Apuesta $1 en TODOS los juegos (sin filtro) para comparar |

**Métricas económicas a calcular** (por estrategia):

| Métrica | Fórmula | Umbral |
|---------|---------|--------|
| ROI | total_profit / total_staked | > 0% |
| Yield | total_profit / n_bets | Informativo |
| Win Rate | n_wins / n_bets | Informativo |
| Max Drawdown | max(peak - trough) / peak | < 30% |
| Profit acumulado | cumsum(profits) | Gráfica |
| N° apuestas | count(bets) | Informativo |
| Sharpe ratio | mean(returns) / std(returns) | > 0 |

**Pasos del script**:
1. Cargar modelo v1.6.0 y datos de test (misma partición temporal)
2. Generar predicciones P(home_win) para test set
3. Obtener odds: si `implied_prob_home` disponible, usar odds reales (`1/implied_prob`). Si no, generar odds simuladas: `odds_home = 1 / (home_win_rate + vig)` con vig = 0.05 (margen de casa de apuestas típico)
4. Para cada estrategia:
   - Determinar qué juegos se apuestan
   - Calcular profit/loss por juego
   - Calcular métricas acumuladas
5. Generar tabla resumen
6. Guardar en `ML/reports/backtesting_results.json`

**Kelly Criterion** — fórmula:
```
f* = (p × o - 1) / (o - 1)
   donde p = probabilidad predicha
         o = odds decimales

Apuesta = max(0, 0.25 × f*) × bankroll
(fracción 25% para reducir volatilidad)
```

**Funciones a reusar**:
- `ML/src/evaluation/metrics.py`: `compute_expected_value()`, `compute_economic_metrics()`
- `ML/src/training/train.py`: `load_ml_ready_games()`, `build_feature_matrix()`
- `ML/src/evaluation/validation.py`: `temporal_train_test_split()`

**Funciones nuevas requeridas**:
- `kelly_fraction(p, odds)` → float: cálculo de fracción de Kelly (inline en el script, no crear utilidad separada)

### Verificación

```bash
python -m scripts.backtesting
```

**Criterios de éxito**:
- [ ] Las 3 estrategias aparecen en la tabla de salida
- [ ] ROI de "Flat en todos" es probablemente negativo (confirma que el filtro de EV importa)
- [ ] Kelly fraccional tiene drawdown menor que stake fijo
- [ ] Max drawdown está documentado para cada estrategia
- [ ] Si se usan odds simuladas, hay un WARNING visible en la salida
- [ ] El JSON se genera correctamente en `ML/reports/backtesting_results.json`
- [ ] N° de apuestas > 0 para al menos la estrategia de "Flat en todos"
- [ ] Profit acumulado es una serie temporal, no un solo número

---

## Entregable 3: Visualización de Calibración (`ML/scripts/plot_calibration.py`)

### Objetivo
Generar gráficas de calibración que demuestren visualmente que el modelo está bien calibrado (ECE = 0.0363). Esto soporta el argumento central: calibración > accuracy.

### Implementación

**Archivo**: `ML/scripts/plot_calibration.py`

**Gráficas a generar**:

| # | Gráfica | Archivo de salida |
|---|---------|------------------|
| 1 | **Reliability diagram** (v1.6.0) | `ML/reports/figures/calibration_v160.png` |
| 2 | **Reliability diagram comparativo** (RF solo vs Ensemble) | `ML/reports/figures/calibration_comparison.png` |
| 3 | **Histograma de confianza** | `ML/reports/figures/confidence_histogram.png` |
| 4 | **Matriz de confusión** | `ML/reports/figures/confusion_matrix.png` |

**Pasos del script**:
1. Cargar modelo v1.6.0 y datos test (misma partición)
2. Generar predicciones
3. Para reliability diagram:
   - Dividir predicciones en 10 bins equidistantes [0, 0.1), [0.1, 0.2), ..., [0.9, 1.0]
   - Para cada bin: calcular `mean(y_true)` (frecuencia real) y `mean(y_proba)` (confianza promedio)
   - Graficar: eje X = confianza predicha, eje Y = frecuencia observada
   - Línea diagonal = calibración perfecta
   - Barras de tamaño de muestra por bin (eje secundario)
   - Anotar ECE en la gráfica
4. Para comparativo: hacer lo mismo con RF solo (entrenar RF con `NBARandomForest`)
5. Histograma de confianza: distribución de P(home_win) del ensemble
6. Matriz de confusión: usar `sklearn.metrics.confusion_matrix` con threshold=0.5

**Librerías**:
- `matplotlib` (ya en requirements.txt vía scikit-learn)
- `numpy` (ya instalado)
- Crear directorio `ML/reports/figures/` si no existe

**Funciones a reusar**:
- `ML/src/training/train.py`: `load_ml_ready_games()`, `build_feature_matrix()`
- `ML/src/evaluation/validation.py`: `temporal_train_test_split()`
- `ML/src/models/random_forest.py`: `NBARandomForest`

### Verificación

```bash
python -m scripts.plot_calibration
```

**Criterios de éxito**:
- [ ] Se generan 4 archivos PNG en `ML/reports/figures/`
- [ ] Reliability diagram muestra puntos cercanos a la diagonal (consistente con ECE 0.0363)
- [ ] El RF solo muestra peor calibración que el ensemble (diferencia visible)
- [ ] Histograma muestra que la mayoría de predicciones están entre 0.4-0.7 (no extremas)
- [ ] Matriz de confusión tiene más aciertos que errores en la diagonal
- [ ] Las gráficas tienen títulos, labels, y leyendas legibles
- [ ] No hay errores de rendering (verificar que matplotlib backend no-GUI funciona: `matplotlib.use('Agg')`)

---

## Entregable 4: Backtesting Visual (`ML/scripts/plot_backtesting.py`)

### Objetivo
Gráficas de profit acumulado y drawdown para complementar el Entregable 2.

### Implementación

**Archivo**: `ML/scripts/plot_backtesting.py`

**Dependencia**: Requiere que `ML/reports/backtesting_results.json` exista (Entregable 2 debe ejecutarse primero).

**Gráficas a generar**:

| # | Gráfica | Archivo |
|---|---------|---------|
| 1 | **Profit acumulado** (3 estrategias) | `ML/reports/figures/cumulative_profit.png` |
| 2 | **Drawdown** (3 estrategias) | `ML/reports/figures/drawdown.png` |
| 3 | **Distribución de apuestas** (EV histogram) | `ML/reports/figures/ev_distribution.png` |

**Pasos**:
1. Cargar resultados del backtesting (JSON o recalcular)
2. Para profit acumulado: `plt.plot(cumsum(profits))` por estrategia
3. Para drawdown: calcular `running_max - current` y graficar
4. Para distribución EV: histograma de expected value por apuesta

**Funciones a reusar**: Las mismas del Entregable 2 si se recalcula.

### Verificación

```bash
python -m scripts.plot_backtesting
```

**Criterios de éxito**:
- [ ] Se generan 3 archivos PNG en `ML/reports/figures/`
- [ ] Profit acumulado muestra las 3 estrategias en colores distintos con leyenda
- [ ] Drawdown es siempre ≤ 0 (por definición)
- [ ] Si ROI es negativo, la curva de profit termina debajo de 0 (honestidad)
- [ ] Distribución EV muestra dónde se concentran los valores esperados

---

## Entregable 5: Agregar Kelly Criterion a `metrics.py`

### Objetivo
Complementar `compute_economic_metrics()` con Kelly criterion.

### Implementación

**Archivo a modificar**: `ML/src/evaluation/metrics.py`

**Cambios**:
1. Agregar función `compute_kelly_fraction(p, odds_decimal)`:
   ```python
   def compute_kelly_fraction(p: float, odds_decimal: float, fraction: float = 0.25) -> float:
       """Kelly criterion con fracción de seguridad."""
       edge = p * odds_decimal - 1
       if edge <= 0:
           return 0.0
       f_star = edge / (odds_decimal - 1)
       return max(0.0, fraction * f_star)
   ```
2. Integrar en `compute_economic_metrics()`: agregar columna `kelly_stake` al output
3. Agregar `avg_kelly_stake` y `kelly_roi` al diccionario de retorno

**Funciones existentes que se modifican**:
- `compute_economic_metrics()` (líneas 189-261): agregar lógica de Kelly al loop de apuestas
- `print_economic_report()`: agregar Kelly metrics al output

### Verificación

```bash
python -c "from src.evaluation.metrics import compute_kelly_fraction; print(compute_kelly_fraction(0.6, 2.0))"
# Esperado: 0.25 * ((0.6*2-1)/(2-1)) = 0.25 * 0.2 = 0.05
```

**Criterios de éxito**:
- [ ] `compute_kelly_fraction(0.6, 2.0, 0.25)` retorna 0.05
- [ ] `compute_kelly_fraction(0.4, 2.0)` retorna 0.0 (sin edge)
- [ ] `compute_kelly_fraction(0.7, 1.5, 0.25)` retorna un valor positivo
- [ ] `compute_economic_metrics()` sigue funcionando igual que antes (backwards compatible)
- [ ] Los tests existentes (si hay) no se rompen
- [ ] `print_economic_report()` muestra Kelly metrics cuando están disponibles

---

## Entregable 6: Documentación del Pipeline E2E (`ML/docs/pipeline.md`)

### Objetivo
Sección para el documento de tesis que explica el pipeline completo y por qué evita leakage, sesgo temporal y sobreajuste.

### Contenido

```
1. Recolección de datos
   - Fuentes: ESPN API (schedule, boxscores, standings, injuries)
   - Cobertura: 3 temporadas (2023-24, 2024-25, 2025-26)
   - Tablas: espn.games, espn.nba_player_boxscores, espn.injuries, espn.odds

2. Limpieza y normalización
   - Reparación de fechas corruptas (scrape_espn_schedule.py)
   - Normalización de nombres de equipos (normalize_team())
   - Resolución de IDs ESPN→NBA (game_id_mapping)
   - Filtrado de juegos con score=0

3. Ingeniería de variables
   - 21 features: 11 diferenciales + 10 individuales
   - Anti-leakage: shift(1) en todos los rolling windows
   - Fórmulas: Possessions, Off/Def Rating, Net Rating, Pace

4. Entrenamiento
   - Ensemble: RF (clasificador calibrado) + XGBoost (regresor de scores)
   - Stacking con LogisticRegression como meta-learner
   - OOF temporal con 5 folds (sin leakage en meta-features)

5. Validación temporal
   - Split 80/20 cronológico (nunca aleatorio)
   - Expanding window CV con min_train_size=0.40
   - Verificación explícita de que no hay datos futuros

6. Calibración
   - RF: CalibratedClassifierCV con Isotonic Regression (cv=5)
   - Ensemble: Isotonic Regression sobre predicciones OOF
   - ECE = 0.0363 (objetivo < 0.05)

7. Exportación
   - Formato: joblib + JSON metadata
   - Ruta: ML/models/ → Backend/ml/models/

8. Integración
   - Backend (FastAPI): carga modelo, genera predicciones, cache 5 min
   - Frontend (React): muestra probabilidades y recomendaciones

9. Monitoreo y versionado
   - 11 versiones entrenadas (v1.0.0 → v1.6.0)
   - Registro en sys.model_versions
   - Comparación via compare_models.py
```

### Verificación

- [ ] El documento cubre los 9 pasos del pipeline
- [ ] Cada paso referencia el archivo de código correspondiente
- [ ] Se explica explícitamente dónde y cómo se previene data leakage
- [ ] Se menciona la validación temporal como requisito obligatorio
- [ ] Se documenta la fórmula de posesiones y ratings

---

## Entregable 7: Documentación de Features (`ML/docs/features.md`)

### Objetivo
Listar todas las variables del modelo, justificar por qué tienen sentido, y separar variables actuales de futuras.

### Contenido

**Variables actuales (v1.6.0) — 21 features**:

| Feature | Tipo | Ventana | Justificación |
|---------|------|---------|--------------|
| `ppg_diff` | Diferencial | 5 juegos | Indicador directo de capacidad ofensiva relativa |
| `net_rating_diff_rolling` | Diferencial | 10 juegos | Métrica estándar NBA de rendimiento neto |
| `rest_days_diff` | Diferencial | N/A | Fatiga demostrada como factor en rendimiento NBA |
| `injuries_diff` | Diferencial | N/A | Impacto de ausencias en plantilla |
| `pace_diff` | Diferencial | 5 juegos | Estilo de juego: ritmo alto/bajo afecta matchups |
| `off_rating_diff` | Diferencial | 5 juegos | Eficiencia ofensiva por 100 posesiones |
| `def_rating_diff` | Diferencial | 5 juegos | Eficiencia defensiva por 100 posesiones |
| `reb_rolling_diff` | Diferencial | 5 juegos | Control del tablero = segundas oportunidades |
| `ast_rolling_diff` | Diferencial | 5 juegos | Juego en equipo y creación de tiros |
| `tov_rolling_diff` | Diferencial | 5 juegos | Cuidado del balón; turnovers regalan posesiones |
| `win_rate_diff` | Diferencial | 10 juegos | Forma reciente del equipo |
| `home_ppg_last5` / `away_ppg_last5` | Individual | 5 juegos | Capacidad anotadora absoluta |
| `home_rest_days` / `away_rest_days` | Individual | N/A | Fatiga absoluta |
| `home_b2b` / `away_b2b` | Individual | N/A | Back-to-back games: efecto negativo documentado |
| `home_injuries_count` / `away_injuries_count` | Individual | N/A | Disponibilidad de plantilla |
| `home_win_rate_last10` / `away_win_rate_last10` | Individual | 10 juegos | Racha/forma del equipo |

**Variables planeadas para v1.7.0+ (experimental)**:

| Feature | Justificación | Bloqueante |
|---------|---------------|-----------|
| Cuotas históricas del mercado | Sabiduría del mercado como feature, no solo para EV | Solo 1% de cobertura actual |
| Distancia de viaje | Fatiga acumulada por viajes | Requiere geocodificación de arenas |
| Historial H2H reciente | Matchups específicos entre equipos | Requiere query adicional |
| Racha de victorias/derrotas | Momentum psicológico | Fácil de implementar |
| Minutos de jugadores clave | Impacto de rotación | Requiere más boxscores |

### Verificación

- [ ] Las 21 features coinciden exactamente con `v1.6.0_metadata.json`
- [ ] Cada feature tiene justificación basada en conocimiento de NBA
- [ ] Las features futuras están claramente separadas como "experimental"
- [ ] Se documenta que todas las rolling usan shift(1)

---

## Entregable 8: Documentación de Evaluación (`ML/docs/evaluation.md`)

### Objetivo
Explicar qué significa cada métrica y por qué la calibración importa más que accuracy para apuestas.

### Contenido

**Métricas primarias**:

| Métrica | Qué mide | v1.6.0 | Umbral | Interpretación |
|---------|----------|--------|--------|---------------|
| **Accuracy** | % de predicciones correctas | 62.1% | N/A | Útil pero engañoso: no distingue confianza |
| **Log Loss** | Penaliza predicciones confiadas pero incorrectas | 0.6553 | < 0.68 | Cuanto menor, mejores probabilidades |
| **Brier Score** | MSE de probabilidades vs resultados | 0.2312 | < 0.25 | Similar a Log Loss pero menos sensible a extremos |
| **ROC-AUC** | Capacidad de discriminación | 0.6542 | > 0.55 | 0.5 = azar, 1.0 = perfecto. 0.65 es moderado |
| **ECE** | Error de calibración esperado | 0.0363 | < 0.05 | Diferencia promedio entre confianza y realidad |

**Argumento central**:
> Un modelo con 62% accuracy pero probabilidades bien calibradas (ECE 0.036) es más útil para apuestas que uno con 68% accuracy y probabilidades poco confiables (ECE 0.15). La razón: en apuestas, la decisión depende de si la probabilidad predicha es mayor que la implícita en la cuota. Si las probabilidades están mal calibradas, el cálculo de Expected Value es incorrecto, y el apostador tomará decisiones subóptimas independientemente del accuracy.

**Secciones adicionales**:
- Curva de calibración (referencia a gráficas del Entregable 3)
- Matriz de confusión (referencia a gráfica del Entregable 3)
- Comparación vs baselines (referencia a tabla del Entregable 1)
- Honestidad sobre ROC-AUC 0.6542: moderado, hay margen de mejora
- Honestidad sobre accuracy 62.1%: no implica rentabilidad automática

### Verificación

- [ ] Se explican las 5 métricas con lenguaje accesible
- [ ] Se justifica por qué calibración > accuracy para apuestas
- [ ] Se admite honestamente que ROC-AUC es moderado
- [ ] Se referencia la curva de calibración del Entregable 3
- [ ] Se incluye la fórmula de ECE

---

## Entregable 9: Documentación de Limitaciones (`ML/docs/limitations.md`)

### Contenido

| Limitación | Impacto | Mitigación |
|-----------|---------|-----------|
| 245 juegos de LA Clippers sin game_id_mapping (2023-25) | Subrepresentación de un equipo en features avanzadas | Documentado; requiere VPN para stats.nba.com |
| ~15 boxscores faltantes de marzo 2026 | Mínimo; están en el borde del test set | Reintentar con `scrape_missing_2026_boxscores.py` |
| 18 juegos con score=0 | Filtrados en entrenamiento | Juegos cancelados o datos no disponibles en ESPN |
| Solo ~1% de juegos tienen odds históricas | Backtesting económico limitado | Se usan odds simuladas (documentado) |
| Dependencia de scraping externo | Fragilidad en recolección de datos | APIs cambian; ESPN y NBA bloquean bots |
| stats.nba.com bloqueado desde esta IP | No se puede obtener boxscores antiguos | Usar VPN o proxy diferente |
| Posible drift entre temporadas | Modelo entrenado en 2023-26 puede degradar en 2026-27 | Reentrenamiento periódico requerido |
| Sin datos de lesiones detallados | Solo count, no severidad ni jugador específico | Feature futura planificada |
| Ventaja de local inflada post-COVID | Home win rate puede no ser estable históricamente | Monitorear en temporadas futuras |
| Base stats (FG%, Reb, etc.) en ml_ready_games tienen leakage | Solo usadas por XGBoost regresor, no por clasificador RF | Documentado; features del clasificador son rolling con shift(1) |

### Verificación

- [ ] Se listan al menos 8 limitaciones
- [ ] Cada una tiene impacto y mitigación
- [ ] No se ocultan debilidades (el documento gana credibilidad)
- [ ] Se menciona el problema de Clippers
- [ ] Se documenta la dependencia de odds simuladas

---

## Entregable 10: Hoja de Ruta Experimental (`ML/docs/roadmap.md`)

### Contenido

**Claramente separado del baseline v1.6.0.**

| Fase | Mejora | Complejidad | Impacto esperado |
|------|--------|-------------|-----------------|
| v1.7.0 | Integrar racha de victorias/derrotas | Baja | Mejora menor en accuracy |
| v1.7.0 | Agregar historial H2H (últimos 5 enfrentamientos) | Media | Puede capturar matchups específicos |
| v1.8.0 | Integrar cuotas históricas como feature | Alta (requiere más datos) | Potencialmente el mayor salto en ROC-AUC |
| v1.8.0 | Fatiga por viajes (distancia entre ciudades) | Media | Relevante para B2B en costa opuesta |
| v2.0.0 | Redes neuronales (LSTM para secuencias temporales) | Alta | Capturar patrones temporales complejos |
| v2.0.0 | Modelos secuenciales (cuartos, parciales) | Alta | Predicciones in-game |
| Continuo | Monitoreo de drift en producción | Media | Detectar degradación antes de que sea crítica |
| Continuo | Reentrenamiento automático (CI/CD pipeline) | Alta | Mantener modelo actualizado |

### Verificación

- [ ] Cada mejora tiene versión tentativa, complejidad e impacto
- [ ] Se separa claramente de v1.6.0
- [ ] No promete resultados, solo planifica experimentación

---

## Orden de Ejecución

```
Fase 1: Código (scripts nuevos)
  1. Entregable 5: Kelly criterion en metrics.py          ← modificación menor
  2. Entregable 1: Script de baselines                     ← depende de modelos existentes
  3. Entregable 2: Script de backtesting                   ← depende de Kelly (E5)
  4. Entregable 3: Plots de calibración                    ← independiente
  5. Entregable 4: Plots de backtesting                    ← depende de E2

Fase 2: Documentación (archivos .md)
  6. Entregable 7: Features                                ← independiente
  7. Entregable 6: Pipeline E2E                            ← independiente
  8. Entregable 8: Evaluación                              ← depende de E1, E3
  9. Entregable 9: Limitaciones                            ← independiente
  10. Entregable 10: Hoja de ruta                          ← independiente

Dependencias:
  E5 → E2 → E4 (Kelly → Backtesting → Plots de backtesting)
  E1 → E8 (Baselines → Evaluación doc referencia resultados)
  E3 → E8 (Calibración plots → Evaluación doc referencia gráficas)
```

---

## Resumen de Archivos

### Archivos nuevos a crear
| Archivo | Tipo | Entregable |
|---------|------|-----------|
| `ML/scripts/baselines.py` | Script Python | E1 |
| `ML/scripts/backtesting.py` | Script Python | E2 |
| `ML/scripts/plot_calibration.py` | Script Python | E3 |
| `ML/scripts/plot_backtesting.py` | Script Python | E4 |
| `ML/reports/baselines_comparison.json` | Output | E1 (generado) |
| `ML/reports/backtesting_results.json` | Output | E2 (generado) |
| `ML/reports/figures/*.png` | Output | E3, E4 (generados) |
| `ML/docs/pipeline.md` | Documentación | E6 |
| `ML/docs/features.md` | Documentación | E7 |
| `ML/docs/evaluation.md` | Documentación | E8 |
| `ML/docs/limitations.md` | Documentación | E9 |
| `ML/docs/roadmap.md` | Documentación | E10 |

### Archivos existentes a modificar
| Archivo | Cambio | Entregable |
|---------|--------|-----------|
| `ML/src/evaluation/metrics.py` | Agregar `compute_kelly_fraction()` + integrar en `compute_economic_metrics()` | E5 |

### Archivos existentes que se REUSAN sin modificar
| Archivo | Funciones usadas |
|---------|-----------------|
| `ML/src/training/train.py` | `load_ml_ready_games()`, `build_feature_matrix()` |
| `ML/src/evaluation/validation.py` | `temporal_train_test_split()` |
| `ML/src/evaluation/metrics.py` | `evaluate_classifier()`, `compute_expected_value()` |
| `ML/src/models/random_forest.py` | `NBARandomForest` |
| `ML/src/models/ensemble.py` | `NBAEnsemble` |
| `ML/models/nba_prediction_model_v1.6.0.joblib` | Modelo oficial |
