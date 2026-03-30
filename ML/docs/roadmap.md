# Hoja de Ruta Experimental

> **Importante**: Todo lo descrito en este documento es experimental y **no forma parte del baseline v1.6.0**. La versión oficial de tesis es v1.6.0, congelada con las métricas reportadas. Las mejoras aquí listadas son propuestas para iteraciones futuras.

## Mejoras de corto plazo (v1.7.0)

| Mejora | Complejidad | Impacto esperado | Notas |
|--------|-------------|------------------|-------|
| **Racha de victorias/derrotas** | Baja | Mejora menor en accuracy | Feature fácil de calcular: `consecutive_wins` o `consecutive_losses` como rolling. Captura momentum psicológico. |
| **Historial H2H reciente** | Media | Captura matchups específicos | Calcular win rate de equipo A vs equipo B en últimos 5 enfrentamientos. Algunos matchups son asimétricos. |
| **Optimización de hiperparámetros** | Media | Posible mejora en Log Loss | Bayesian optimization con Optuna sobre expanding window CV. Cuidado con sobreajuste al test set. |

## Mejoras de mediano plazo (v1.8.0)

| Mejora | Complejidad | Impacto esperado | Notas |
|--------|-------------|------------------|-------|
| **Cuotas históricas como feature** | Alta (datos) | Potencialmente el mayor salto en ROC-AUC | La "sabiduría del mercado" es un predictor fuerte. Requiere obtener cuotas históricas de APIs de apuestas (The Odds API, etc.). Actualmente solo ~1% de cobertura. |
| **Fatiga por viajes** | Media | Relevante para B2B en costa opuesta | Geocodificar las 30 arenas NBA y calcular distancia de viaje entre partidos consecutivos. Un B2B con viaje NY→LA es diferente a NY→Boston. |
| **Impacto de lesiones por jugador** | Alta (datos) | Mejora en injury features | Ponderar lesiones por VORP o Win Shares del jugador. La ausencia de un MVP impacta más que la de un reserva. |

## Mejoras de largo plazo (v2.0.0+)

| Mejora | Complejidad | Impacto esperado | Notas |
|--------|-------------|------------------|-------|
| **Redes neuronales (LSTM)** | Alta | Capturar patrones temporales complejos | Modelar la secuencia de resultados como serie temporal. Requiere significativamente más datos y tuning. |
| **Modelos secuenciales (in-game)** | Alta | Predicciones en tiempo real durante el partido | Usar datos de parciales (cuartos) para actualizar probabilidades. Requiere streaming de datos. |
| **Ensemble más amplio** | Media | Diversificación de modelos | Agregar LightGBM, CatBoost, o redes neuronales como base learners adicionales. |

## Infraestructura

| Mejora | Complejidad | Impacto | Notas |
|--------|-------------|---------|-------|
| **Monitoreo de drift** | Media | Detectar degradación antes de que sea crítica | Comparar distribución de features y métricas del modelo en producción vs entrenamiento. Alertas si ECE o Log Loss degradan. |
| **Reentrenamiento automático** | Alta | Mantener modelo actualizado sin intervención | CI/CD pipeline que reentrena mensualmente con datos nuevos, valida métricas, y despliega si pasan criterios. |
| **A/B testing en producción** | Alta | Comparar versiones en vivo | Servir dos versiones simultáneamente y comparar métricas de negocio (user engagement, accuracy en producción). |

## Criterio para promocionar experimentales

Una versión experimental se promueve a "candidata a nuevo baseline" solo si:
1. Pasa **todos** los criterios de aceptación (Log Loss < 0.68, Brier < 0.25, ROC-AUC > 0.55, ECE < 0.05)
2. Mejora **al menos una** métrica sin degradar significativamente las otras
3. Se evalúa sobre el **mismo test set** temporal para comparación justa
4. El cambio es **reproducible** (mismo random_state=42, mismos datos)
