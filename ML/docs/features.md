# Variables del Modelo — v1.6.0

## Resumen

El modelo utiliza **21 features** organizadas en dos categorías:
- **11 features diferenciales**: `home_value - away_value`, reducen dimensionalidad e incrementan interpretabilidad
- **10 features individuales**: valores absolutos cuando el diferencial no es suficiente

Todas las features de tipo rolling utilizan `shift(1)` para garantizar que solo se usan datos de partidos **anteriores**, previniendo data leakage.

## Variables actuales (v1.6.0)

### Features diferenciales (11)

| Feature | Ventana | Fórmula | Justificación |
|---------|---------|---------|--------------|
| `ppg_diff` | 5 juegos | `home_ppg_last5 - away_ppg_last5` | Indicador directo de capacidad ofensiva relativa. Un equipo que anota más puntos por juego tiene mayor probabilidad de ganar. |
| `net_rating_diff_rolling` | 10 juegos | `home_net_rating_last10 - away_net_rating_last10` | Métrica estándar de la NBA. Net Rating = Off Rating - Def Rating. Captura rendimiento global del equipo, no solo puntos anotados. |
| `rest_days_diff` | N/A | `home_rest_days - away_rest_days` | La fatiga está documentada como factor significativo en rendimiento NBA. Equipos con más descanso rinden mejor. |
| `injuries_diff` | N/A | `home_injuries_count - away_injuries_count` | Más lesiones implican menos talento disponible. La diferencia captura la ventaja relativa por salud de plantilla. |
| `pace_diff` | 5 juegos | `home_pace_rolling - away_pace_rolling` | El ritmo de juego afecta matchups. Un equipo rápido contra uno lento genera asimetría táctica. Pace = posesiones por 48 minutos. |
| `off_rating_diff` | 5 juegos | `home_off_rating_rolling - away_off_rating_rolling` | Eficiencia ofensiva por 100 posesiones. Normaliza por ritmo de juego, aislando la calidad ofensiva pura. |
| `def_rating_diff` | 5 juegos | `home_def_rating_rolling - away_def_rating_rolling` | Eficiencia defensiva por 100 posesiones. Un Def Rating menor indica mejor defensa. |
| `reb_rolling_diff` | 5 juegos | `home_reb_rolling - away_reb_rolling` | Control del tablero = segundas oportunidades ofensivas y menos para el rival. |
| `ast_rolling_diff` | 5 juegos | `home_ast_rolling - away_ast_rolling` | Proxy de juego en equipo y creación de tiros de calidad. |
| `tov_rolling_diff` | 5 juegos | `home_tov_rolling - away_tov_rolling` | Turnovers regalan posesiones al rival. Menos turnovers = más eficiencia. |
| `win_rate_diff` | 10 juegos | `home_win_rate_last10 - away_win_rate_last10` | Forma reciente del equipo. Captura momentum y tendencia de resultados. |

### Features individuales (10)

| Feature | Ventana | Justificación |
|---------|---------|--------------|
| `home_ppg_last5` | 5 juegos | Capacidad anotadora absoluta del local. Complementa el diferencial cuando un equipo es consistentemente alto/bajo. |
| `away_ppg_last5` | 5 juegos | Capacidad anotadora absoluta del visitante. |
| `home_rest_days` | N/A | Días desde el último juego del local. Importante en absoluto: 1 día (B2B) es diferente a 2+ días sin importar el rival. |
| `away_rest_days` | N/A | Días desde el último juego del visitante. |
| `home_b2b` | N/A | Booleano: `rest_days == 1`. Jugar partidos consecutivos tiene un efecto negativo documentado en la NBA. |
| `away_b2b` | N/A | Booleano: el visitante juega back-to-back. |
| `home_injuries_count` | N/A | Número de jugadores lesionados del local. El conteo absoluto importa: 5 lesiones son más impactantes que 0 vs 1. |
| `away_injuries_count` | N/A | Número de jugadores lesionados del visitante. |
| `home_win_rate_last10` | 10 juegos | Porcentaje de victorias del local en últimos 10 juegos. Valor absoluto muestra si el equipo está en racha. |
| `away_win_rate_last10` | 10 juegos | Porcentaje de victorias del visitante en últimos 10 juegos. |

## Fórmulas clave

### Posesiones (NBA estándar simplificada)
```
Possessions = FGA + 0.44 × FTA - OReb + TOV
```

### Ratings por 100 posesiones
```
Offensive Rating = (Points / Possessions) × 100
Defensive Rating = (Opponent Points / Possessions) × 100
Net Rating       = Offensive Rating - Defensive Rating
```

### Anti-leakage
Todas las features rolling se calculan con `shift(1)`:
```python
feature = series.shift(1).rolling(window).mean()
```
Esto garantiza que al calcular features para el juego N, solo se usan datos de juegos 1 a N-1.

## Features excluidas del clasificador

Las siguientes columnas existen en `ml.ml_ready_games` pero **NO se usan** como features del clasificador porque contienen datos del partido actual (leakage):
- `reb_diff`, `ast_diff`, `tov_diff` (diferenciales del partido actual)
- `home_fg_pct`, `home_3p_pct`, `home_ft_pct` (estadísticas del partido actual)
- `home_reb`, `home_ast`, `home_stl`, `home_blk`, `home_to`

Estas se mantienen en la tabla para el regresor XGBoost (que predice scores) y para análisis post-partido.

## Variables planeadas para futuras versiones (experimental)

| Feature | Versión | Justificación | Bloqueante |
|---------|---------|---------------|-----------|
| Racha de victorias/derrotas | v1.7.0 | Momentum psicológico; equipos en racha tienden a mantenerla | Fácil de implementar |
| Historial H2H (últimos 5 enfrentamientos) | v1.7.0 | Matchups específicos entre equipos; ciertos estilos dominan a otros | Requiere query adicional |
| Cuotas históricas del mercado | v1.8.0 | La sabiduría colectiva del mercado como feature predictiva | Solo ~1% de cobertura actual |
| Distancia de viaje | v1.8.0 | Fatiga acumulada por viajes; relevante para B2B en costa opuesta | Requiere geocodificación de arenas |
| Minutos de jugadores clave | v2.0.0 | Rotaciones y minutos de estrellas impactan resultado | Requiere boxscores más completos |

Estas variables **no forman parte del baseline v1.6.0** y su implementación es experimental.
