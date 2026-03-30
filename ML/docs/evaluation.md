# Evaluación del Modelo — v1.6.0

## Métricas primarias

| Métrica | Valor | Umbral | Pasa | Qué mide |
|---------|-------|--------|------|----------|
| **Log Loss** | 0.6553 | < 0.68 | ✅ | Calidad de las probabilidades predichas. Penaliza fuertemente predicciones confiadas pero incorrectas. |
| **Brier Score** | 0.2312 | < 0.25 | ✅ | Error cuadrático medio entre probabilidades y resultados. Similar a Log Loss pero menos sensible a extremos. Baseline naive (0.5) = 0.25. |
| **ROC-AUC** | 0.6542 | > 0.55 | ✅ | Capacidad de discriminación: qué tan bien separa victorias de derrotas. 0.5 = azar, 1.0 = perfecto. |
| **ECE** | 0.0363 | < 0.05 | ✅ | Error de Calibración Esperado: diferencia promedio ponderada entre confianza predicha y frecuencia real. |
| **Accuracy** | 62.1% | N/A | — | Porcentaje de predicciones correctas con umbral 0.5. |

**Tamaño del test set**: 734 partidos (20% más reciente del dataset)

## Explicación de cada métrica

### Accuracy (62.1%)

La métrica más intuitiva pero también la más engañosa. Mide qué porcentaje de partidos el modelo predice correctamente (usando umbral P=0.5). Sin embargo:

- **No distingue confianza**: una predicción con P=0.51 y una con P=0.99 cuentan igual si aciertan.
- **No penaliza probabilidades malas**: un modelo que dice "90% de confianza" pero se equivoca paga el mismo costo que uno que dice "51%".
- Para apuestas, saber *cuánto* confiar importa tanto como *acertar*.

### Log Loss (0.6553)

Métrica principal de entrenamiento. Penaliza exponencialmente las predicciones confiadas que se equivocan:

```
Log Loss = -1/N × Σ [y × log(p) + (1-y) × log(1-p)]
```

Un modelo que dice "95% seguro" y se equivoca recibe una penalización mucho mayor que uno que dice "55% seguro" y se equivoca. Esto incentiva al modelo a ser honesto con su incertidumbre.

**Baseline**: Log Loss de un predictor naive (P=0.5 siempre) = 0.693 (ln 2). Nuestro 0.6553 es mejor que el azar.

### Brier Score (0.2312)

Error cuadrático medio entre la probabilidad predicha y el resultado real (0 o 1):

```
Brier = 1/N × Σ (p - y)²
```

**Baseline**: predictor naive (P=0.5) tiene Brier = 0.25. Un Brier más bajo indica mejores probabilidades.

A diferencia de Log Loss, Brier es menos sensible a predicciones extremas incorrectas, lo que lo hace más robusto pero menos discriminante.

### ROC-AUC (0.6542)

Mide la capacidad del modelo para separar victorias locales de derrotas locales, independientemente del umbral de decisión.

- **0.50** = modelo aleatorio (no separa nada)
- **0.65** = separación moderada
- **0.75+** = buena separación
- **1.00** = separación perfecta

**Honestidad**: Un ROC-AUC de 0.6542 es moderado. El modelo tiene capacidad de discriminación real pero hay margen significativo de mejora. Esto es esperado en predicción deportiva, donde la incertidumbre inherente al juego limita la predictibilidad.

### ECE — Expected Calibration Error (0.0363)

La métrica más importante para apuestas. Mide qué tan bien las probabilidades reflejan la realidad:

```
ECE = Σ (n_bin / N) × |accuracy_bin - confidence_bin|
```

Se divide las predicciones en 10 bins de igual ancho (0-10%, 10-20%, ..., 90-100%). Para cada bin se calcula:
- **Confianza promedio**: media de las probabilidades predichas
- **Frecuencia real**: porcentaje de veces que realmente ganó el local

Un ECE = 0 significa calibración perfecta. Nuestro ECE = 0.0363 indica que la diferencia promedio entre lo que el modelo dice y lo que ocurre es de ~3.6 puntos porcentuales.

## Por qué la calibración importa más que accuracy para apuestas

**Argumento central**: Un modelo con 62% accuracy pero probabilidades bien calibradas (ECE 0.036) es más útil para apuestas que uno con 68% accuracy y probabilidades poco confiables (ECE 0.15).

**Razón**: En apuestas deportivas, la decisión no es "¿quién va a ganar?" sino "¿esta probabilidad es mayor que la implícita en la cuota?".

El cálculo de Expected Value (EV) es:
```
EV = P(ganar) × cuota_decimal - 1
```

Si `P(ganar)` no es confiable (modelo mal calibrado), el cálculo de EV es incorrecto, y el apostador tomará decisiones subóptimas independientemente del accuracy. Un modelo que dice "70% seguro" cuando la realidad es 55% generará falsos positivos de EV, llevando a apuestas con ventaja aparente pero pérdida real.

En contraste, un modelo con menor accuracy pero buena calibración permite calcular EV correctamente, identificar verdaderas apuestas de valor, y tomar decisiones rentables a largo plazo.

## Curva de calibración

Ver: `ML/reports/figures/calibration_v160.png`

La curva de calibración (reliability diagram) muestra la frecuencia observada vs. la confianza predicha por bin. Puntos cercanos a la diagonal indican buena calibración.

## Matriz de confusión

Ver: `ML/reports/figures/confusion_matrix.png`

## Comparación contra baselines

El ensemble supera a todos los baselines evaluados. Ver resultados completos en `ML/reports/baselines_comparison.json` y la tabla comparativa generada por `ML/scripts/baselines.py`.

Baselines evaluados:
1. Siempre local (P=1.0)
2. Moneda al aire (P=0.5)
3. Home win rate fijo (proporción histórica)
4. Logistic Regression (mismas 21 features)
5. Random Forest solo (sin ensemble)
6. XGBoost clasificador solo

## Nota sobre ROC-AUC moderado

Un ROC-AUC de 0.6542 refleja la realidad de la predicción deportiva: los partidos de NBA tienen alta variabilidad inherente. Factores no capturados (rendimiento individual en el día, decisiones arbitrales, "clutch moments") limitan la predictibilidad de cualquier modelo.

Esto no invalida el modelo — un ROC-AUC consistentemente por encima de 0.55 con buena calibración sigue siendo útil para identificar apuestas de valor. Pero es importante no sobreinterpretar los resultados ni sugerir que el modelo "resuelve" la predicción deportiva.

## Nota sobre accuracy y rentabilidad

Un accuracy de 62.1% **no implica automáticamente** rentabilidad en apuestas. Si el mercado (las casas de apuestas) ya refleja correctamente las probabilidades, un modelo puede acertar más que el azar y aun así no encontrar apuestas de valor.

La rentabilidad depende de:
1. Que el modelo identifique correctamente situaciones donde el mercado subestima a un equipo
2. Que la frecuencia de estas oportunidades sea suficiente
3. Que el margen de ventaja (edge) supere el vigorish de la casa de apuestas

Ver backtesting de rentabilidad: `ML/reports/backtesting_results.json`
