# Variables del Modelo — v3.1.0

## Resumen

El modelo activo (v3.1.0) utiliza **52 features**:
- **18 features diferenciales base** (v2.0.0): `home_value - away_value`
- **15 features individuales base** (v2.0.0): valores absolutos
- **14 features V3** (v3.0.0): rest flags, player top-3, margen rolling, strength composite
- **3 features V3.1** (v3.1.0): porcentajes de tiro rolling (FG%, 3P%, FT%)
- **2 features de mercado** (v3.1.0, activadas por defecto): probabilidades implícitas de cuotas

Todas las features de tipo rolling utilizan `shift(1)` para garantizar que solo se usan datos de partidos **anteriores**, previniendo data leakage.

## Variables base (v2.0.0: 33)

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

## Variables V3 (v3.0.0: +14)

| Feature | Tipo | Justificación |
|---------|------|--------------|
| `home_big_rest`, `away_big_rest` | Flag | Descanso ≥3 días: ventaja documentada (Entine & Small, 2008). |
| `home_optimal_rest`, `away_optimal_rest` | Flag | Exactamente 2 días: punto óptimo entre descanso y ritmo. |
| `home_excessive_rest`, `away_excessive_rest` | Flag | ≥5 días: efecto negativo por pérdida de ritmo. |
| `home_player_top3_pts`, `away_player_top3_pts` | Rolling 5 | Puntos combinados del top-3 de anotadores (boxscores de jugadores). |
| `home_player_top3_eff`, `away_player_top3_eff` | Rolling 5 | Eficiencia combinada del top-3. |
| `avg_margin_diff` | Rolling 5 | Diferencial de margen promedio de victoria/derrota. |
| `player_top3_pts_advantage`, `player_top3_eff_advantage` | Diferencial | Ventaja relativa de estrellas. |
| `strength_composite` | Compuesto | `0.4×elo_diff/100 + 0.35×net_rating_diff/10 + 0.25×win_rate_diff`. |

## Variables V3.1 (v3.1.0: +5)

| Feature | Ventana | Fórmula | Justificación |
|---------|---------|---------|--------------|
| `fg_pct_rolling_diff` | 5 juegos | `home_fg_pct_rolling - away_fg_pct_rolling` | FG% reciente (doc sustentación §2.3.1). Rolling con `shift(1)` — la versión por-partido (`home_fg_pct`) sigue excluida por leakage. |
| `fg3_pct_rolling_diff` | 5 juegos | `home_3p_pct_rolling - away_3p_pct_rolling` | 3P% reciente. Complementa a eFG% aislando el tiro exterior. |
| `ft_pct_rolling_diff` | 5 juegos | `home_ft_pct_rolling - away_ft_pct_rolling` | FT% reciente. Señal de ejecución en la línea, decisiva en finales cerrados. |
| `implied_prob_home` | Por partido | `(1/cuota_home) / Σ(1/cuotas)` | Probabilidad implícita del mercado sin vig (doc §2.3.4). Cobertura ~1.3%; filas sin cuotas se pre-imputan con la mediana del training set (~0.53, no informativo). |
| `implied_prob_away` | Por partido | `(1/cuota_away) / Σ(1/cuotas)` | Complemento visitante. |

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
- `home_fg_pct`, `home_3p_pct`, `home_ft_pct` (estadísticas del partido actual; sus versiones rolling `*_rolling` SÍ son features desde v3.1.0)
- `home_reb`, `home_ast`, `home_stl`, `home_blk`, `home_to`

Estas se mantienen en la tabla para el regresor XGBoost (que predice scores) y para análisis post-partido.

## Variables planeadas para futuras versiones

| Feature | Justificación | Bloqueante |
|---------|---------------|-----------|
| Distancia de viaje | Fatiga acumulada por viajes; relevante para B2B en costa opuesta | Requiere geocodificación de arenas |
| Minutos de jugadores clave | Rotaciones y minutos de estrellas (más granular que top-3 pts/eff) | Requiere pipeline de player props por minuto |

## Changelog de features

| Versión | Cambios |
|---------|---------|
| v1.6.0 | 21 features base (11 diff + 10 individual). Baseline congelado. |
| v2.0.0 | +12 features: EFG%, TOV Rate, OReb%, DReb%, Elo, Streak, H/A splits, H2H (7 diff + 5 individual). Total: 33 features. |
| v2.2.0 | +2 features de odds (`implied_prob_*`, opt-in). Total: 35. Team-props como outputs (no features). |
| v3.0.0 | +14 features V3: rest flags, player top-3, margen rolling, strength_composite (sin odds). Total: 47. |
| v3.1.0 | +3 shooting rolling (FG%/3P%/FT%) y odds activadas por defecto. Total: **52**. |
