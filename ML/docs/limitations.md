# Limitaciones del Sistema

## Limitaciones de datos

| Limitación | Impacto | Mitigación |
|-----------|---------|-----------|
| **~15 juegos sin boxscore recuperable** | Juegos con score pero sin boxscore debido a errores 502/DNS de NBA.com. Features rolling se calculan con NaN para esos partidos. | Errores transitorios de red. Se pueden reintentar. Impacto mínimo dado el total de 3,765 juegos jugados. |
| **130 juegos con score=0** | Filtrados del entrenamiento. Incluyen juegos futuros (108), postponed (11) y datos no disponibles. | Se filtran automáticamente en `build_feature_matrix()`. No afectan el modelo. |
| **Clippers: recuperados pero con gaps residuales** | Se recuperaron ~153 boxscores de Clippers (2023-25) que faltaban originalmente. Quedan ~5 juegos irrecuperables por errores 502. | Cobertura pasó de ~0% a ~98% para Clippers. El gap residual es despreciable. |
| **Solo ~1% de juegos tienen odds históricas** | El backtesting económico es indicativo, no definitivo. No se puede validar rigurosamente la rentabilidad real. | Se generan odds simuladas con vigorish típico (5%) para backtesting. Los resultados se documentan claramente como simulados. |
| **Sin datos de lesiones detallados** | Solo se cuenta el número de lesionados, no la severidad ni el jugador específico. La ausencia de LeBron James no pesa igual que la de un jugador de rotación. | Feature futura planificada para v2.0.0. Requiere mapeo de impacto por jugador (ej: VORP, Win Shares). |

## Limitaciones técnicas

| Limitación | Impacto | Mitigación |
|-----------|---------|-----------|
| **Dependencia de scraping externo** | Las fuentes (ESPN, NBA.com) pueden cambiar sus APIs o bloquear bots en cualquier momento, quebrando el pipeline de datos. | Múltiples scrapers alternativos implementados. Logs de errores y scripts de auditoría para detectar quiebres. |
| **stats.nba.com bloqueado** | No se pueden obtener boxscores históricos directamente desde esta IP. | Mitigado con `scrape_new_boxscores.py` que usa CDN de NBA.com y `__NEXT_DATA__` de nba.com/game. Cobertura actual: 99.7%. |
| **Base stats en ml_ready_games tienen leakage** | Columnas como `home_fg_pct`, `home_reb` contienen datos del partido actual. | Estas columnas NO se usan como features del clasificador. Solo las features rolling con `shift(1)` se incluyen. Documentado en `train.py` líneas 44-57. |

## Limitaciones del modelo

| Limitación | Impacto | Mitigación |
|-----------|---------|-----------|
| **ROC-AUC moderado (0.6180)** | El modelo tiene capacidad de discriminación real pero no excepcional. No separa perfectamente victorias de derrotas. | Esperado en predicción deportiva. La alta variabilidad inherente de los partidos de NBA limita la predictibilidad de cualquier modelo. |
| **Accuracy ≠ Rentabilidad** | 58.17% de accuracy no garantiza ganancias si el mercado ya refleja bien las probabilidades. | Se documenta en la sección de evaluación. El backtesting simula rentabilidad con odds realistas. |
| **Degradación en test set reciente** | Las métricas empeoran en el test set v2 (dic 2025 - mar 2026) vs el original. Log Loss pasa de 0.6553 a 0.6932, ECE de 0.0363 a 0.0834. | Drift temporal esperado. El modelo fue entrenado con datos hasta ~dic 2025 y no se re-entrenó. Confirma la necesidad de reentrenamiento periódico. |
| **Posible drift entre temporadas** | El modelo entrenado con datos 2023-26 puede degradar en la temporada 2026-27 si cambian las dinámicas del juego (nuevas reglas, fichajes, etc.). | Reentrenamiento periódico requerido. Monitoreo de drift en producción es una mejora planificada. |
| **Ventaja de local puede fluctuar** | El home win rate (~57%) puede no ser estable históricamente (fue diferente pre/post-COVID). Si cambia significativamente, el modelo podría estar sobre/subestimando la ventaja local. | Monitorear home win rate por temporada en futuras iteraciones. |
| **Sin modelado de series temporales** | El modelo trata cada juego como independiente (features rolling son un proxy). No captura dependencias temporales complejas (rachas, momentum extendido). | Mejora planificada para v2.0.0 con LSTM o modelos secuenciales. |
| **Calibración isotónica puede sobreajustar** | Con datasets pequeños, la isotonic regression puede memorizar patrones del train set. | Mitigado con OOF: la calibración del ensemble se entrena sobre predicciones out-of-fold, no sobre el train set directo. |

## Transparencia sobre la evaluación

1. **Las métricas se calculan sobre un test set de 753 partidos (v2)**. El test set cubre dic 2025 a mar 2026.
2. **No se realizó búsqueda exhaustiva de hiperparámetros** (por diseño, para evitar sobreajuste).
3. **El backtesting económico usa odds simuladas** (indicativo, no definitivo). Solo ~1% de juegos tienen odds reales.
4. **La corrección de data leakage redujo el accuracy** de ~70% a ~62% (v1), y la evaluación con datos recientes lo sitúa en ~58% (v2). Esto confirma que el modelo original estaba inflado y que el rendimiento real es más conservador.
5. **242 boxscores fueron recuperados** tras la evaluación original, mejorando la cobertura de datos de ~93% a ~99.7%. Las features ahora reflejan datos más completos, especialmente para LA Clippers y marzo 2026.
