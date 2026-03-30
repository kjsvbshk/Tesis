# Limitaciones del Sistema

## Limitaciones de datos

| Limitación | Impacto | Mitigación |
|-----------|---------|-----------|
| **245 juegos de LA Clippers sin game_id_mapping (2023-25)** | Subrepresentación de un equipo en features avanzadas (off_rating, def_rating, pace). Puede introducir un sesgo menor si el modelo ve menos datos de Clippers que de otros equipos. | Documentado. El scraper original omitió los Clippers. stats.nba.com bloquea conexiones desde esta IP, imposibilitando obtener los NBA game IDs. Requiere VPN o proxy diferente. |
| **~15 boxscores faltantes de marzo 2026** | Mínimo. Están en el borde del test set y no afectan significativamente las métricas. | Reintentar con `scrape_missing_2026_boxscores.py`. Error original fue SSL/red transitorio. |
| **18 juegos con score=0** | Filtrados del entrenamiento. No afectan el modelo pero reducen ligeramente el dataset. | Juegos cancelados (LA wildfires enero 2025) o datos no disponibles en ESPN API. Se filtran en `build_feature_matrix()`. |
| **Solo ~1% de juegos tienen odds históricas** | El backtesting económico es indicativo, no definitivo. No se puede validar rigurosamente la rentabilidad real. | Se generan odds simuladas con vigorish típico (5%) para backtesting. Los resultados se documentan claramente como simulados. |
| **Sin datos de lesiones detallados** | Solo se cuenta el número de lesionados, no la severidad ni el jugador específico. La ausencia de LeBron James no pesa igual que la de un jugador de rotación. | Feature futura planificada para v2.0.0. Requiere mapeo de impacto por jugador (ej: VORP, Win Shares). |

## Limitaciones técnicas

| Limitación | Impacto | Mitigación |
|-----------|---------|-----------|
| **Dependencia de scraping externo** | Las fuentes (ESPN, NBA.com) pueden cambiar sus APIs o bloquear bots en cualquier momento, quebrando el pipeline de datos. | Múltiples scrapers alternativos implementados. Logs de errores y scripts de auditoría para detectar quiebres. |
| **stats.nba.com bloqueado** | No se pueden obtener boxscores históricos de temporadas anteriores (2023-25) desde esta IP. | cdn.nba.com funciona para 2025-26. Para temporadas anteriores se requiere VPN. |
| **Base stats en ml_ready_games tienen leakage** | Columnas como `home_fg_pct`, `home_reb` contienen datos del partido actual. | Estas columnas NO se usan como features del clasificador. Solo las features rolling con `shift(1)` se incluyen. Documentado en `train.py` líneas 44-57. |

## Limitaciones del modelo

| Limitación | Impacto | Mitigación |
|-----------|---------|-----------|
| **ROC-AUC moderado (0.6542)** | El modelo tiene capacidad de discriminación real pero no excepcional. No separa perfectamente victorias de derrotas. | Esperado en predicción deportiva. La alta variabilidad inherente de los partidos de NBA limita la predictibilidad de cualquier modelo. |
| **Accuracy ≠ Rentabilidad** | 62.1% de accuracy no garantiza ganancias si el mercado ya refleja bien las probabilidades. | Se documenta en la sección de evaluación. El backtesting simula rentabilidad con odds realistas. |
| **Posible drift entre temporadas** | El modelo entrenado con datos 2023-26 puede degradar en la temporada 2026-27 si cambian las dinámicas del juego (nuevas reglas, fichajes, etc.). | Reentrenamiento periódico requerido. Monitoreo de drift en producción es una mejora planificada. |
| **Ventaja de local puede fluctuar** | El home win rate (~57%) puede no ser estable históricamente (fue diferente pre/post-COVID). Si cambia significativamente, el modelo podría estar sobre/subestimando la ventaja local. | Monitorear home win rate por temporada en futuras iteraciones. |
| **Sin modelado de series temporales** | El modelo trata cada juego como independiente (features rolling son un proxy). No captura dependencias temporales complejas (rachas, momentum extendido). | Mejora planificada para v2.0.0 con LSTM o modelos secuenciales. |
| **Calibración isotónica puede sobreajustar** | Con datasets pequeños, la isotonic regression puede memorizar patrones del train set. | Mitigado con OOF: la calibración del ensemble se entrena sobre predicciones out-of-fold, no sobre el train set directo. |

## Transparencia sobre la evaluación

1. **Las métricas se calculan sobre un test set de 734 partidos**. Con más datos futuros, las métricas podrían variar.
2. **No se realizó búsqueda exhaustiva de hiperparámetros** (por diseño, para evitar sobreajuste).
3. **El backtesting económico usa odds simuladas** (indicativo, no definitivo).
4. **La corrección de data leakage redujo el accuracy** de ~70% a ~62%, lo que confirma que el modelo anterior estaba inflado pero también que el modelo actual es más honesto.
