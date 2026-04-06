# Variables del Modelo — v2.0.0

## Resumen

El modelo utiliza **33 features** organizadas en dos categorías:
- **18 features diferenciales**: `home_value - away_value`, reducen dimensionalidad e incrementan interpretabilidad
- **15 features individuales**: valores absolutos cuando el diferencial no es suficiente

Todas las features de tipo rolling utilizan `shift(1)` para garantizar que solo se usan datos de partidos **anteriores**, previniendo data leakage.

## Variables actuales (v2.0.0)

### Features diferenciales (18)

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
| `efg_pct_diff` | 5 juegos | `home_efg_pct_rolling - away_efg_pct_rolling` | EFG% (Effective FG%) pondera triples con +50%. Mejor indicador de eficiencia de tiro que FG% simple. |
| `tov_rate_diff` | 5 juegos | `home_tov_rate_rolling - away_tov_rate_rolling` | Turnover Rate = TOV / (FGA + 0.44×FTA + TOV). Normaliza pérdidas por posesiones usadas. |
| `oreb_pct_diff` | 5 juegos | `home_oreb_pct_rolling - away_oreb_pct_rolling` | OReb% = OREB / (OREB + OPP_DREB). Capacidad de generar segundas oportunidades. |
| `dreb_pct_diff` | 5 juegos | `home_dreb_pct_rolling - away_dreb_pct_rolling` | DReb% = DREB / (DREB + OPP_OREB). Capacidad de negar segundas oportunidades al rival. |
| `elo_diff` | Acumulativo | `home_elo - away_elo` | Rating Elo (K=20, home_adv=100). Incorpora toda la historia de resultados, convergente y auto-correctivo. |
| `streak_diff` | N/A | `home_streak - away_streak` | Racha actual: positivo=victorias consecutivas, negativo=derrotas. Captura momentum. |
| `home_away_split_diff` | 10 juegos | `home_home_win_rate - away_away_win_rate` | Win rate específico por localía. Algunos equipos rinden muy diferente en casa vs fuera. |

### Features individuales (15)

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
| `home_elo` | Acumulativo | Rating Elo del local entrando al juego. Sistema acumulativo con K=20 y home advantage=100. |
| `away_elo` | Acumulativo | Rating Elo del visitante entrando al juego. |
| `home_streak` | N/A | Racha del local antes del juego. +N = N victorias consecutivas, -N = N derrotas. |
| `away_streak` | N/A | Racha del visitante antes del juego. |
| `h2h_home_advantage` | 5 enfrentamientos | Fracción de victorias del local en los últimos 5 enfrentamientos directos entre estos dos equipos (normalizado 0-1). |

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

### Effective Field Goal % (EFG%)
```
EFG% = (FGM + 0.5 × 3PM) / FGA
```
Pondera triples como 1.5 tiros de campo, reflejando su mayor valor. Es un mejor indicador de eficiencia de tiro que FG% simple.

### Turnover Rate
```
Turnover Rate = TOV / (FGA + 0.44 × FTA + TOV)
```
Normaliza las pérdidas por el número de posesiones usadas, no por juego. El factor 0.44 ajusta los tiros libres por posesión.

### Rebound Percentages
```
OReb% = OREB / (OREB + OPP_DREB)
DReb% = DREB / (DREB + OPP_OREB)
```
Miden la capacidad de capturar rebotes como porcentaje de los rebotes disponibles, no en valor absoluto.

### Elo Rating
```
Expected = 1 / (1 + 10^((Opp_Elo - Elo - Home_Adv) / 400))
New_Elo = Old_Elo + K × (Actual - Expected)
```
Con K=20, Home_Advantage=100, Elo_inicial=1500. Se calcula cronológicamente sobre toda la historia; el Elo entrando a un juego solo refleja resultados anteriores (sin leakage por diseño).

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

## Variables planeadas para futuras versiones

| Feature | Versión | Justificación | Bloqueante |
|---------|---------|---------------|-----------|
| Cuotas históricas del mercado | v2.1.0 | La sabiduría colectiva del mercado como feature predictiva | Solo ~1% de cobertura actual |
| Distancia de viaje | v2.1.0 | Fatiga acumulada por viajes; relevante para B2B en costa opuesta | Requiere geocodificación de arenas |
| Minutos de jugadores clave | v3.0.0 | Rotaciones y minutos de estrellas impactan resultado | Requiere pipeline de player props |

## Changelog de features

| Versión | Cambios |
|---------|---------|
| v1.6.0 | 21 features base (11 diff + 10 individual). Baseline congelado. |
| v2.0.0 | +12 features: EFG%, TOV Rate, OReb%, DReb%, Elo, Streak, H/A splits, H2H (7 diff + 5 individual). Total: 33 features. |
