# Model Specification — NBA Betting Predictive System

## 1. Propósito del Modelo

El objetivo de este sistema es estimar **probabilidades calibradas de victoria del equipo local (P(home_win))** en partidos de la NBA, con el fin de evaluar oportunidades de apuesta con **valor esperado positivo (EV)** frente a las cuotas del mercado.

El modelo **no optimiza directamente ganancias**, sino la **calidad probabilística** de las predicciones. La rentabilidad se evalúa posteriormente mediante simulación económica (backtesting).

---

## 2. Definición Formal del Problema

### 2.1 Tipo de Problema

* Tipo: Clasificación binaria probabilística
* Variable objetivo (target): `home_win`

  * Definición:

    * 1 si el equipo local gana el partido
    * 0 si el equipo visitante gana

### 2.2 Horizonte Temporal

* Predicción realizada **antes del inicio del partido**
* Solo se utilizan datos disponibles hasta la fecha del partido
* Está explícitamente prohibido el uso de información posterior (anti-leakage)

---

## 3. Variable Objetivo

### 3.1 Target Primario

* Nombre: `home_win`
* Tipo: Boolean / Binario
* Dominio: {0, 1}

### 3.2 Targets Secundarios (Auxiliares, No Optimizados)

Los siguientes targets **no forman parte de la función objetivo principal**, pero pueden utilizarse como features auxiliares o outputs interpretativos:

* `home_score` (regresión)
* `away_score` (regresión)

Estos targets se emplean únicamente para:

* Baselines estadísticos (modelo Poisson)
* Interpretación del resultado
* Features en modelos ensemble

---

## 4. Función Objetivo y Métricas

### 4.1 Función Objetivo de Entrenamiento

El entrenamiento de los modelos de clasificación optimiza la **log loss**:

$$
\mathcal{L}_{log} = - \frac{1}{N} \sum_{i=1}^{N} \left[y_i \log(p_i) + (1 - y_i) \log(1 - p_i) \right]
$$

Donde:

* $y_i$ es el valor real de `home_win`
* $p_i$ es la probabilidad predicha de victoria local

### 4.2 Métricas Predictivas Primarias

* Log Loss (métrica principal)
* Brier Score

### 4.3 Métricas Predictivas Secundarias

* Accuracy
* ROC-AUC
* Calibration Error (ECE)

### 4.4 Métricas Económicas (Evaluación Posterior)

Estas métricas **no se usan para entrenar el modelo**, solo para evaluación experimental:

* Valor Esperado (EV)
* ROI
* Drawdown máximo
* Win Rate

---

## 5. Política de Decisión de Apuestas

### 5.1 Definición de Valor Esperado

Dado:

* $p = P(\text{home\_win})$
* $o$ = cuota decimal del mercado

El valor esperado de una apuesta se define como:

$$
EV = p \times o - 1
$$

### 5.2 Regla de Decisión

Una apuesta se recomienda **únicamente si**:

* $EV > \tau_{EV}$
* $p > \tau_{confianza}$

Donde:

* $\tau_{EV} = 0.05$ (5% de edge mínimo)
* $\tau_{confianza} = 0.55$

Si no se cumplen ambas condiciones, **no se realiza apuesta**.

---

## 6. Granularidad y Estructura del Dataset

### 6.1 Unidad de Observación

* Una fila representa **un partido**
* No se generan filas por equipo

### 6.2 Formato de Features

Se utiliza un enfoque **diferencial**, donde cada feature representa la diferencia entre el equipo local y visitante:

$$
X_{diff} = X_{home} - X_{away}
$$

Ejemplos:

* `ppg_diff`
* `net_rating_diff`
* `rest_days_diff`
* `injuries_diff`

Este enfoque reduce dimensionalidad y facilita la interpretación del modelo.

---

## 7. Restricciones Metodológicas

* Prohibido el uso de validación aleatoria (train_test_split)
* Todos los splits deben ser **temporales**
* Las probabilidades deben estar calibradas
* Todos los experimentos deben ser reproducibles (random seed fijo)

---

## 8. Criterios de Aceptación del Modelo

### 8.1 Predictivos

* Log Loss < 0.68
* Brier Score < 0.25
* ROC-AUC > 0.55
* Calibration Error < 0.05

### 8.2 Económicos (Backtest)

* ROI > 0% en periodo de test
* ROI mejor que baseline aleatorio
* Drawdown máximo < 30%

---

## 9. Alcance del Proyecto

Este documento define el **alcance académico mínimo** del sistema.

Quedan fuera del alcance obligatorio:

* Monitoreo en producción
* Reentrenamiento automático
* Optimización extrema de hiperparámetros

Estos aspectos se documentan como **trabajo futuro**.

---

## 10. Versionado

* Dataset inicial: v1.0.0
* Modelo inicial: v1.0.0
* Cambios en targets o métricas implican incremento mayor de versión
