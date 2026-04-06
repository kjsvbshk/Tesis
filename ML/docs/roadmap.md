# Hoja de Ruta — Niveles de Predicción

> **Estado actual**: Nivel 1 implementado (v2.0.0). Niveles 2-4 documentados como trabajo futuro.

## Nivel 1 — Core Predictions (v2.0.0) ✅ IMPLEMENTADO

### Targets
| Target | Modelo | Tipo | Métricas |
|--------|--------|------|----------|
| **P(home_win)** | Ensemble (RF + XGBoost → LogReg + Isotonic) | Clasificación | Log Loss, Brier, ROC-AUC, ECE, Accuracy |
| **Margen esperado** | XGBRegressor dedicado (NBAMarginModel) | Regresión | MAE, RMSE, Bias, Correlación |
| **Total puntos** | XGBRegressor dedicado (NBATotalModel) | Regresión | MAE, RMSE, Bias, Correlación |

### Features (33 total)
- 18 diferenciales + 15 individuales
- Incluye: EFG%, Turnover Rate, OReb%, DReb%, Elo, Streak, Home/Away splits, H2H
- Todas con `shift(1)` anti-leakage
- Ver detalle en `features.md`

### Criterios de aceptación
| Métrica | Umbral | Aplica a |
|---------|--------|----------|
| Log Loss | < 0.68 | home_win |
| Brier Score | < 0.25 | home_win |
| ROC-AUC | > 0.55 | home_win |
| ECE | < 0.05 | home_win |
| MAE margen | < 10.0 pts | margin |
| MAE total | < 15.0 pts | total |

---

## Nivel 2 — Betting Market Predictions (v2.1.0) 📋 PLANEADO

### Targets
| Target | Descripción | Dependencia |
|--------|-------------|-------------|
| **Spread cover** | `cover = 1 si (home_score - away_score) > spread_line` | Requiere líneas de spread históricas |
| **Over/Under** | `over = 1 si (home_score + away_score) > total_line` | Requiere líneas O/U históricas |
| **Implied fair odds** | Comparar probabilidades del modelo vs mercado para detectar value bets | Requiere odds históricas completas |

### Datos requeridos
- **Líneas de spread históricas** (ej: Lakers -5.5) — no disponible actualmente
- **Líneas de Over/Under** (ej: Total 228.5) — no disponible actualmente
- **Odds de múltiples casas** — solo ~1% de cobertura actual en `espn.odds`
- **Fuentes potenciales**: The Odds API, sportsbook APIs

### Enfoque de modelado
- Usar predicciones de Nivel 1 (margen, total) como features base
- Agregar la línea de mercado como feature adicional
- Clasificador binario (P(cover), P(over)) entrenado sobre resultados históricos
- Las predicciones de margen y total ya dan una ventaja: si `predicted_margin > spread`, es señal de cover

### Bloqueantes
1. Baja cobertura de datos de odds (~1%)
2. Requiere API de terceros o scraping adicional
3. Las líneas cambian antes de cada juego (timing del dato importa)

---

## Nivel 3 — Team Props (v2.2.0) 📋 PLANEADO

### Targets
| Target | Descripción | Complejidad |
|--------|-------------|-------------|
| **P(home_team_over_X_points)** | Equipo local supera X puntos | Media |
| **P(away_team_over_X_points)** | Equipo visitante supera X puntos | Media |
| **P(home_wins_first_half)** | Local gana la primera mitad | Alta |
| **P(home_wins_Q1)** | Local gana primer cuarto | Alta |
| **P(team_over_X_threes)** | Equipo supera X triples | Media |

### Datos requeridos
- Datos de parciales por cuarto/mitad (no disponibles actualmente)
- Líneas de props de equipo de casas de apuestas
- Boxscores detallados con breakdown por cuarto

### Enfoque de modelado
- Regresor por equipo (predicted_home_points, predicted_away_points) → ya existe en XGBoost
- Clasificador binario para cada prop: `P(team_points > line)`
- Features de ritmo (pace) son clave para props de totales

### Bloqueantes
1. Sin datos de cuartos/mitades en la DB actual
2. Sin líneas de props de equipo históricas
3. Mayor volatilidad que moneyline

---

## Nivel 4 — Player Props (v3.0.0) 📋 PLANEADO

### Targets
| Target | Ejemplo | Complejidad |
|--------|---------|-------------|
| **Puntos O/U** | P(LeBron > 27.5 pts) | Alta |
| **Rebotes O/U** | P(Jokic > 11.5 reb) | Alta |
| **Asistencias O/U** | P(Haliburton > 9.5 ast) | Alta |
| **Triples O/U** | P(Curry > 4.5 threes) | Alta |
| **PRA** | P(jugador > 45.5 PRA) | Alta |
| **Doble-doble / Triple-doble** | P(Jokic triple-double) | Alta |

### Datos disponibles
- `espn.nba_player_boxscores` (267K+ registros): pts, reb, ast, stl, blk, tov, fg%, 3p%, ft%, oreb, dreb
- Cobertura: 2023-10 a 2026-03

### Pipeline adicional requerido
1. **Rolling stats por jugador**: Promedios last-5, last-10 de cada stat (puntos, rebotes, etc.)
2. **Predicción de minutos**: Modelo que prediga minutos esperados (clave para props)
3. **Matchup features**: Stats defensivas del equipo rival vs posición del jugador
4. **Injury/availability**: Verificar que el jugador esté activo antes de predecir
5. **Rotación**: Cambios de rol (titular→suplente) afectan drasticamente los stats

### Bloqueantes
1. Sin feature engineering a nivel jugador (solo agregado a equipo)
2. Sin datos de minutos consistentes en la DB
3. Sin líneas de player props históricas
4. Requiere modelo por tipo de stat (puntos, rebotes, etc.)
5. Alta volatilidad y variabilidad game-to-game

---

## Orden de implementación recomendado

```
Nivel 1 (Core)           ← v2.0.0 [HECHO]
  │
  ├── Nivel 2 (Betting)  ← v2.1.0 [requiere datos de odds]
  │     │
  │     └── Nivel 3 (Team Props) ← v2.2.0 [requiere datos de cuartos]
  │
  └── Nivel 4 (Player Props) ← v3.0.0 [requiere nuevo pipeline]
```

Los Niveles 2 y 3 comparten features de equipo del Nivel 1. El Nivel 4 es independiente y requiere un pipeline completamente nuevo a nivel jugador.

## Criterio para promocionar versiones

Una versión se promueve a "candidata a nuevo baseline" solo si:
1. Pasa **todos** los criterios de aceptación del nivel correspondiente
2. Mejora **al menos una** métrica sin degradar significativamente las otras
3. Se evalúa sobre el **mismo test set** temporal para comparación justa
4. El cambio es **reproducible** (mismo random_state=42, mismos datos)
