# Evaluación del Modelo — v1.6.0

## Métricas primarias

| Métrica | Valor | Umbral | Pasa | Qué mide |
|---------|-------|--------|------|----------|
| **Log Loss** | 0.6932 | < 0.68 | ❌ | Calidad de las probabilidades predichas. Penaliza fuertemente predicciones confiadas pero incorrectas. |
| **Brier Score** | 0.2479 | < 0.25 | ✅ | Error cuadrático medio entre probabilidades y resultados. Similar a Log Loss pero menos sensible a extremos. Baseline naive (0.5) = 0.25. |
| **ROC-AUC** | 0.6180 | > 0.55 | ✅ | Capacidad de discriminación: qué tan bien separa victorias de derrotas. 0.5 = azar, 1.0 = perfecto. |
| **ECE** | 0.0834 | < 0.05 | ❌ | Error de Calibración Esperado: diferencia promedio ponderada entre confianza predicha y frecuencia real. |
| **Accuracy** | 58.17% | N/A | — | Porcentaje de predicciones correctas con umbral 0.5. |

**Tamaño del test set**: 753 partidos (20% más reciente del dataset, hasta 2026-03-29)

**Nota**: Estas métricas se evaluaron con datos corregidos (242 boxscores recuperados de Clippers + marzo 2026) y un test set que cubre diciembre 2025 a marzo 2026. El modelo v1.6.0 no fue re-entrenado; las métricas reflejan su rendimiento sobre datos más completos y recientes.

## Explicación de cada métrica

### Accuracy (58.17%)

La métrica más intuitiva pero también la más engañosa. Mide qué porcentaje de partidos el modelo predice correctamente (usando umbral P=0.5). Sin embargo:

- **No distingue confianza**: una predicción con P=0.51 y una con P=0.99 cuentan igual si aciertan.
- **No penaliza probabilidades malas**: un modelo que dice "90% de confianza" pero se equivoca paga el mismo costo que uno que dice "51%".
- Para apuestas, saber *cuánto* confiar importa tanto como *acertar*.

### Log Loss (0.6932)

Métrica principal de entrenamiento. Penaliza exponencialmente las predicciones confiadas que se equivocan:

```
Log Loss = -1/N × Σ [y × log(p) + (1-y) × log(1-p)]
```

Un modelo que dice "95% seguro" y se equivoca recibe una penalización mucho mayor que uno que dice "55% seguro" y se equivoca. Esto incentiva al modelo a ser honesto con su incertidumbre.

**Baseline**: Log Loss de un predictor naive (P=0.5 siempre) = 0.693 (ln 2). Nuestro 0.6932 está prácticamente al nivel del azar, lo que indica que el modelo no mejora significativamente la calidad probabilística respecto a un predictor ingenuo en este test set.

### Brier Score (0.2479)

Error cuadrático medio entre la probabilidad predicha y el resultado real (0 o 1):

```
Brier = 1/N × Σ (p - y)²
```

**Baseline**: predictor naive (P=0.5) tiene Brier = 0.25. Nuestro 0.2479 es ligeramente mejor que el baseline, indicando una mejora marginal en la calidad probabilística.

A diferencia de Log Loss, Brier es menos sensible a predicciones extremas incorrectas, lo que lo hace más robusto pero menos discriminante.

### ROC-AUC (0.6180)

Mide la capacidad del modelo para separar victorias locales de derrotas locales, independientemente del umbral de decisión.

- **0.50** = modelo aleatorio (no separa nada)
- **0.65** = separación moderada
- **0.75+** = buena separación
- **1.00** = separación perfecta

**Honestidad**: Un ROC-AUC de 0.6180 es moderado. El modelo tiene capacidad de discriminación real pero hay margen significativo de mejora. Esto es esperado en predicción deportiva, donde la incertidumbre inherente al juego limita la predictibilidad.

### ECE — Expected Calibration Error (0.0834)

La métrica más importante para apuestas. Mide qué tan bien las probabilidades reflejan la realidad:

```
ECE = Σ (n_bin / N) × |accuracy_bin - confidence_bin|
```

Se divide las predicciones en 10 bins de igual ancho (0-10%, 10-20%, ..., 90-100%). Para cada bin se calcula:
- **Confianza promedio**: media de las probabilidades predichas
- **Frecuencia real**: porcentaje de veces que realmente ganó el local

Un ECE = 0 significa calibración perfecta. Nuestro ECE = 0.0834 indica que la diferencia promedio entre lo que el modelo dice y lo que ocurre es de ~8.3 puntos porcentuales. Esto no alcanza el umbral objetivo de 0.05, lo que sugiere que la calibración del modelo se degrada en datos más recientes y que un re-entrenamiento con datos actualizados sería beneficioso.

## Por qué la calibración importa más que accuracy para apuestas

**Argumento central**: Un modelo con accuracy moderado pero probabilidades bien calibradas es más útil para apuestas que uno con mayor accuracy pero probabilidades poco confiables.

**Razón**: En apuestas deportivas, la decisión no es "¿quién va a ganar?" sino "¿esta probabilidad es mayor que la implícita en la cuota?".

El cálculo de Expected Value (EV) es:
```
EV = P(ganar) × cuota_decimal - 1
```

Si `P(ganar)` no es confiable (modelo mal calibrado), el cálculo de EV es incorrecto, y el apostador tomará decisiones subóptimas independientemente del accuracy. Un modelo que dice "70% seguro" cuando la realidad es 55% generará falsos positivos de EV, llevando a apuestas con ventaja aparente pero pérdida real.

En contraste, un modelo con menor accuracy pero buena calibración permite calcular EV correctamente, identificar verdaderas apuestas de valor, y tomar decisiones rentables a largo plazo.

## Curva de calibración

Ver: `ML/reports/figures/calibration_v160_v2.png`

La curva de calibración (reliability diagram) muestra la frecuencia observada vs. la confianza predicha por bin. Puntos cercanos a la diagonal indican buena calibración.

## Matriz de confusión

Ver: `ML/reports/figures/confusion_matrix_v2.png`

## Comparación contra baselines

Ver resultados completos en `ML/reports/baselines_comparison_v2.json`.

| Modelo | Log Loss | Brier | ROC-AUC | ECE | Accuracy |
|--------|----------|-------|---------|-----|----------|
| Siempre local | 4.8193 | 0.5231 | 0.5000 | 0.5231 | 47.68% |
| Moneda al aire | 0.6931 | 0.2500 | 0.5000 | 0.0232 | 47.68% |
| Home win rate fijo (54.71%) | 0.7020 | 0.2544 | 0.5000 | 0.0704 | 47.68% |
| Logistic Regression | **0.6858** | **0.2450** | **0.6262** | 0.0867 | 56.97% |
| Random Forest solo | 0.7044 | 0.2510 | 0.6187 | 0.1000 | 57.37% |
| XGBoost clasificador | 0.7257 | 0.2578 | 0.6120 | 0.1125 | **58.43%** |
| **Ensemble v1.6.0** | 0.6932 | 0.2479 | 0.6180 | 0.0834 | 58.17% |

**Observaciones**: En este test set (753 partidos, dic 2025 - mar 2026), Logistic Regression obtiene el mejor Log Loss (0.6858), superando al Ensemble. Todos los modelos ML superan a los baselines heurísticos en ROC-AUC y accuracy. El Ensemble mantiene un balance competitivo entre todas las métricas pero no domina en ninguna individualmente.

## Nota sobre ROC-AUC moderado

Un ROC-AUC de 0.6180 refleja la realidad de la predicción deportiva: los partidos de NBA tienen alta variabilidad inherente. Factores no capturados (rendimiento individual en el día, decisiones arbitrales, "clutch moments") limitan la predictibilidad de cualquier modelo.

Esto no invalida el modelo — un ROC-AUC consistentemente por encima de 0.55 sigue siendo útil para identificar apuestas de valor. Pero es importante no sobreinterpretar los resultados ni sugerir que el modelo "resuelve" la predicción deportiva.

## Nota sobre accuracy y rentabilidad

Un accuracy de 58.17% **no implica automáticamente** rentabilidad en apuestas. Si el mercado (las casas de apuestas) ya refleja correctamente las probabilidades, un modelo puede acertar más que el azar y aun así no encontrar apuestas de valor.

La rentabilidad depende de:
1. Que el modelo identifique correctamente situaciones donde el mercado subestima a un equipo
2. Que la frecuencia de estas oportunidades sea suficiente
3. Que el margen de ventaja (edge) supere el vigorish de la casa de apuestas

Ver backtesting de rentabilidad: `ML/reports/backtesting_results_v2.json`

## Degradación respecto a métricas originales

Las métricas v2 (con datos completos) son peores que las originales (v1). Esto se explica por:
1. **Test set diferente**: El test set v2 cubre dic 2025 - mar 2026 (753 partidos), mientras v1 cubría un periodo anterior (734 partidos).
2. **El modelo no fue re-entrenado**: v1.6.0 fue entrenado con datos hasta ~dic 2025. Los datos de ene-mar 2026 son predicciones sobre un periodo más lejano al entrenamiento.
3. **Drift temporal**: Las dinámicas de la temporada 2025-26 (trades, lesiones, rotaciones) difieren de los datos de entrenamiento.

Esto refuerza la necesidad de **re-entrenamiento periódico** del modelo con datos actualizados.
