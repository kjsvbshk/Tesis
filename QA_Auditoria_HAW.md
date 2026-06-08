# QA Auditoría — Sistema HAW (House Always Wins)
**Fecha:** 2026-06-04 | **Versión:** v2.2.0 | **Auditor:** QA Engineer (automatizado)

---

## Resumen Ejecutivo

| Área | Estado | Críticos | Medios | Bajos |
|------|--------|----------|--------|-------|
| Autenticación y seguridad | ✅ PASA | 0 | 1 | 2 |
| Predicciones ML | ⚠️ OBSERVACIONES | 0 | 3 | 1 |
| Apuestas y créditos | ⚠️ OBSERVACIONES | 0 | 2 | 2 |
| Partidos y odds | ❌ FALLA | 1 | 2 | 1 |
| Infraestructura / patrones | ✅ PASA | 0 | 1 | 2 |

**Total:** 1 crítico · 9 medios · 8 bajos

---

## 1. Autenticación y Gestión de Usuarios

### Casos de prueba ejecutados

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| AU-01 | Registro con email válido + verificación OTP | ✅ IMPLEMENTADO | `EmailService` + `email_verification_codes` |
| AU-02 | Login con JWT Bearer Token | ✅ IMPLEMENTADO | `create_access_token`, argon2 hash |
| AU-03 | Token expirado devuelve 401 | ✅ IMPLEMENTADO | `verify_token` usa `JWTError` |
| AU-04 | Usuario inactivo bloqueado | ✅ IMPLEMENTADO | `is_active` check en `get_current_user` |
| AU-05 | 2FA TOTP con QR code | ✅ IMPLEMENTADO | `pyotp`, backup codes con SHA-256 |
| AU-06 | RBAC — roles admin/operator/client | ✅ IMPLEMENTADO | `require_permission`, `UserRole` tabla |
| AU-07 | Sesiones concurrentes y revocación | ✅ IMPLEMENTADO | `user_sessions` con token_hash |
| AU-08 | Recuperación de contraseña por email | ✅ IMPLEMENTADO | `ForgotPasswordRequest` + OTP |
| AU-09 | Headers de seguridad HTTP | ✅ IMPLEMENTADO | HSTS, X-Frame-Options, CSP |
| AU-10 | Sanitización de datos sensibles en logs | ✅ IMPLEMENTADO | `sanitize_for_logging` |

### Hallazgos

**[MEDIO] AU-M01 — `datetime.utcnow()` deprecated en Python 3.12+**
- **Archivo:** `auth_service.py`, `bet_service.py`, `prediction_service.py` (33 ocurrencias en 12 archivos)
- **Descripción:** `datetime.utcnow()` fue deprecado en Python 3.12. El proyecto usa Python 3.13. Funciona actualmente pero generará `DeprecationWarning` y eventualmente fallará.
- **Fix:** Reemplazar por `datetime.now(timezone.utc)` en todos los servicios.
- **Severidad:** Media (funcional pero técnicamente incorrecto).

**[BAJO] AU-B01 — Token de acceso sin refresh token**
- **Descripción:** El sistema solo emite `access_token`. No existe `refresh_token`. El usuario debe re-autenticarse cuando el token expira.
- **Impacto:** UX degradada (sesión corta), no es un riesgo de seguridad.

**[BAJO] AU-B02 — `security_monitoring` importado pero no conectado a rate limiting**
- **Archivo:** `users.py` importa `security_monitoring` pero no hay lógica de rate limiting activa por IP/usuario.

---

## 2. Predicciones ML

### Casos de prueba ejecutados

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| PR-01 | Predicción de partido histórico (en ml_ready_games) | ✅ IMPLEMENTADO | `FeatureExtractor` + `predict_full_robust` |
| PR-02 | Predicción de partido futuro (LiveFeatureExtractor) | ✅ IMPLEMENTADO | Nuevo en esta sesión |
| PR-03 | 422 cuando party no existe en DB | ✅ IMPLEMENTADO | `FeaturesNotAvailableError` → HTTP 422 |
| PR-04 | 503 cuando modelo no está cargado | ✅ IMPLEMENTADO | `ModelNotLoadedError` → HTTP 503 |
| PR-05 | Detección automática de feature_set (21/33/35) | ✅ IMPLEMENTADO | `detect_feature_set` |
| PR-06 | Idempotencia con X-Idempotency-Key | ✅ IMPLEMENTADO | `check_idempotency_and_register` |
| PR-07 | Team-props en respuesta (rebotes, ast, etc.) | ✅ IMPLEMENTADO | `NBAStatRegressor` × 10 |
| PR-08 | Upcoming games con predicciones en vivo | ✅ IMPLEMENTADO | `get_upcoming_predictions` |
| PR-09 | Caché de predicciones (TTL 5 min) | ✅ IMPLEMENTADO | `cache_service.get_or_set` |
| PR-10 | Telemetría de latencia (`inference_latency_ms`) | ✅ IMPLEMENTADO | Timing aislado del modelo |

### Hallazgos

**[MEDIO] PR-M01 — Schema `PredictionResponse.home_team_id` es `int` (NOT NULL) pero `get_upcoming_predictions` pasa `None`**
- **Archivo:** `prediction_service.py` línea 433-434: `home_team_id=None, away_team_id=None`
- **Descripción:** El schema Pydantic declara `home_team_id: int` (no Optional), pero el nuevo endpoint de upcoming games pasa `None`. Esto causará `ValidationError` de Pydantic en runtime cuando se llame `/predict/upcoming`.
- **Fix:** Cambiar en `prediction.py`:
  ```python
  home_team_id: Optional[int] = None
  away_team_id: Optional[int] = None
  ```
- **Severidad:** Media — bloquea funcionalidad de upcoming games.

**[MEDIO] PR-M02 — `PredictionsPage.tsx` solo acepta input manual de game_id**
- **Descripción:** El usuario debe conocer el `game_id` numérico de ESPN para obtener una predicción. No hay selector de partidos ni dropdown. La integración con `UpcomingGamesPage` mediante botón "ANALYZE" pasa el game_id por URL, lo cual funciona, pero la UX del flujo principal es deficiente.
- **Impacto:** Barrera alta para usuarios finales en demo/defensa.

**[MEDIO] PR-M03 — `latency_ms` (total HTTP) vs `inference_latency_ms` (modelo aislado) — frontend solo muestra uno**
- **Descripción:** El schema backend expone ambos. El frontend (`predictions.service.ts`) tiene ambos campos pero `PredictionsPage.tsx` no muestra `inference_latency_ms` de forma diferenciada visualmente.
- **Impacto:** Bajo para funcionalidad, pero la telemetría que el modelo produce no se visualiza correctamente.

**[BAJO] PR-B01 — `audit_log` para predicciones usa `request_id` como `prediction_id`**
- **Archivo:** `predictions.py` líneas 121, 256: `prediction_id=request_id`
- **Descripción:** El audit log registra `prediction_id` con el valor de `request_id` por falta de una referencia directa al `Prediction` recién creado. Funcionalmente correcto pero semánticamente impreciso.

---

## 3. Apuestas y Créditos

### Casos de prueba ejecutados

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| BT-01 | Colocar apuesta moneyline | ✅ IMPLEMENTADO | `BetService.place_bet` |
| BT-02 | Validar créditos suficientes antes de apostar | ✅ IMPLEMENTADO | `deduct_credits` + rollback |
| BT-03 | Refund automático si falla la apuesta post-débito | ✅ IMPLEMENTADO | `add_credits` en except |
| BT-04 | Cancelar apuesta pendiente (refund) | ✅ IMPLEMENTADO | `cancel_bet` |
| BT-05 | Historial de apuestas por usuario | ✅ IMPLEMENTADO | `get_user_bets` con filtros |
| BT-06 | Transacción registrada en `app.transactions` | ✅ IMPLEMENTADO | `Transaction` con before/after |
| BT-07 | Validar que equipo pertenece al partido | ✅ IMPLEMENTADO | Cross-check `espn.teams` + `espn.games` |
| BT-08 | Estadísticas de apuestas del usuario | ✅ IMPLEMENTADO | `/bets/stats/summary` |
| BT-09 | Liquidación automática de apuestas | ❌ NO IMPLEMENTADO | Sin worker de liquidación |
| BT-10 | Apuesta sobre total (over/under) | ✅ IMPLEMENTADO | `BetType.over_under` |

### Hallazgos

**[MEDIO] BT-M01 — Sin worker de liquidación de apuestas (BT-09)**
- **Descripción:** Las apuestas se crean con `status='pending'` pero nunca se liquidan automáticamente. No existe un proceso que compare el resultado del partido con la apuesta y cambie el estado a `won`/`lost` ni acredite ganancias.
- **Impacto:** El flujo de apuestas está incompleto. Los usuarios nunca ven apuestas ganadas ni reciben créditos por victorias. En producción esto sería crítico; para el prototipo de tesis es una limitación documentable.
- **Workaround:** Liquidación manual vía SQL. Documentar como trabajo futuro.

**[MEDIO] BT-M02 — `espn.bets` y `app.bets` son tablas paralelas con misma funcionalidad**
- **Descripción:** Existen dos modelos de apuestas: `espn.bets` (con `EspnBet`, `BetSelection`, `BetResult`) y `app.bets` (con `Bet` en app schema). `BetService` usa `espn.bets`. `app.bets` tiene 0 filas y no se usa. Hay riesgo de confusión en mantenimiento.
- **Fix:** Eliminar `app.bets` o documentar claramente cuál es la tabla maestra.

**[BAJO] BT-B01 — `BetSlip.tsx` y `BetsPage.tsx` existen pero no se confirma integración end-to-end**
- **Descripción:** Ambos componentes frontend existen y llaman a `betsService`. Sin datos en `espn.bets`, la funcionalidad no puede validarse visualmente.

**[BAJO] BT-B02 — `bet_service.py` importa `get_espn_db` pero no lo usa directamente**
- **Descripción:** Importación no utilizada (`from app.core.database import get_espn_db`). Señal de deuda técnica menor.

---

## 4. Partidos y Odds

### Casos de prueba ejecutados

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| PT-01 | Listado de partidos (`/matches/`) | ✅ IMPLEMENTADO | Query dinámica sobre `espn.games` |
| PT-02 | Partidos de hoy (`/matches/today`) | ✅ IMPLEMENTADO | Filtro por `fecha >= today` |
| PT-03 | Partido específico por ID (`/matches/{id}`) | ✅ IMPLEMENTADO | `get_match_by_id` |
| PT-04 | Partidos próximos con predicciones (`/proximos`) | ✅ IMPLEMENTADO | `UpcomingGamesPage` |
| PT-05 | Odds en respuesta de partidos | ⚠️ PARCIAL | Solo 53 partidos tienen odds (~1.4%) |
| PT-06 | `game_date` en respuesta de partidos | ⚠️ PARCIAL | Fix aplicado, pendiente verificar |
| PT-07 | Pipeline de odds completo (API → DB → implied_prob) | ✅ IMPLEMENTADO | `refresh_odds_pipeline.py` |
| PT-08 | Filtro partidos futuros (score=0, teams != TBD) | ✅ IMPLEMENTADO | `get_upcoming_predictions` |

### Hallazgos

**[CRÍTICO] PT-C01 — `home_team_id` y `away_team_id` son `int` NOT NULL en `PredictionResponse` pero `get_upcoming_predictions` pasa `None`**
- **Descripción:** *(mismo que PR-M01 — duplicado en este contexto porque bloquea el endpoint `/predict/upcoming` que es el núcleo de la página de próximos partidos)*
- **Fix inmediato requerido** — sin este fix, la página `UpcomingGamesPage` siempre falla.

**[MEDIO] PT-M01 — `match_service.get_matches()` imprime 5+ líneas de DEBUG en cada request**
- **Archivo:** `match_service.py` líneas 124-145
- **Descripción:** `print(f"🔍 Columnas encontradas...")`, `print(f"✅ ID column: ...")`, etc. se ejecutan en cada llamada al endpoint. En producción esto llena los logs y degrada el rendimiento.
- **Fix:** Cambiar a `logger.debug(...)` o eliminar.

**[MEDIO] PT-M02 — Caché de `/matches/today` TTL fijo de 5 min no invalida cuando se insertan nuevos partidos**
- **Descripción:** Si se ejecuta el scraper y se insertan nuevos partidos, el dashboard seguirá mostrando datos obsoletos hasta que expire el caché. No hay invalidación activa.
- **Fix:** Añadir invalidación de caché al final del pipeline ETL, o reducir TTL.

**[BAJO] PT-B01 — `home_odds` query en `match_service` por cada partido en el listado (N+1 queries)**
- **Archivo:** `match_service.py` — el fix de odds añade una query SQL extra por cada partido en el listado
- **Descripción:** Para 50 partidos → 50 queries adicionales a `espn.game_odds`. Lento pero funcional para el prototipo.
- **Fix futuro:** JOIN en la query principal.

---

## 5. Infraestructura y Patrones de Calidad

### Casos de prueba ejecutados

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| IF-01 | Patrón Outbox (RF-08) | ✅ IMPLEMENTADO | `OutboxService`, `app.outbox` (91 filas) |
| IF-02 | Audit Log (RF-09) | ✅ IMPLEMENTADO | `AuditService`, `app.audit_log` (123 filas) |
| IF-03 | Idempotencia (RF-06) | ✅ IMPLEMENTADO | `X-Idempotency-Key` header |
| IF-04 | Circuit Breaker (RF-05) | ✅ IMPLEMENTADO | `CircuitBreaker` clase en `circuit_breaker.py` |
| IF-05 | HTTPS y security headers | ✅ IMPLEMENTADO | `SecurityHeadersMiddleware` |
| IF-06 | Caché in-memory con TTL | ✅ IMPLEMENTADO | `cache_service`, stale-while-revalidate |
| IF-07 | Worker outbox publica eventos | ⚠️ PARCIAL | `outbox_worker.py` existe, no verificado en prod |
| IF-08 | Health check endpoint | ✅ IMPLEMENTADO | `/health` |
| IF-09 | Separación de schemas (espn/ml/app/sys) | ✅ IMPLEMENTADO | 4 schemas en Neon, roles separados |
| IF-10 | UNIQUE constraints en tablas críticas | ✅ IMPLEMENTADO | `uq_player_boxscore` aplicado en esta sesión |

### Hallazgos

**[MEDIO] IF-M01 — `app.outbox` tiene 91 filas con `published_at = NULL` — eventos no procesados**
- **Descripción:** El `outbox_worker` escribe en `app.outbox` pero en el entorno local no está corriendo como proceso continuo. Los 91 eventos en la tabla están sin publicar. En producción (Render) tampoco hay evidencia de que el worker esté activo.
- **Impacto:** Los eventos de predicciones completadas nunca se "publican" a consumidores externos. No afecta funcionalidad core del prototipo.

**[BAJO] IF-B01 — `datetime.utcnow()` en 33 lugares (ver AU-M01)**

**[BAJO] IF-B02 — `CircuitBreaker` implementado pero solo referenciado en `provider_orchestrator.py`; no protege endpoints de predicción**
- **Descripción:** El circuit breaker funciona para proveedores externos pero no está aplicado a la carga del modelo ML ni al acceso a Neon. Un fallo de Neon no activa el circuit breaker.

---

## 6. Resumen de Defectos por Severidad

### 🔴 Críticos (1) — Bloquean funcionalidad

| ID | Descripción | Archivo | Fix |
|----|-------------|---------|-----|
| PT-C01 | `home_team_id: int` NOT NULL en schema pero upcoming predictions pasa `None` → `ValidationError` | `app/schemas/prediction.py` línea 31-32 | Cambiar a `Optional[int] = None` |

### 🟡 Medios (9) — Degradan funcionalidad o calidad

| ID | Descripción |
|----|-------------|
| AU-M01 | `datetime.utcnow()` deprecated en Python 3.13 (33 usos) |
| PR-M02 | `PredictionsPage` requiere game_id manual — UX pobre para demo |
| PR-M03 | `inference_latency_ms` no visualizada en dashboard |
| BT-M01 | Sin worker de liquidación de apuestas |
| BT-M02 | Dos tablas de apuestas paralelas (`espn.bets` vs `app.bets`) |
| PT-M01 | 5+ prints de DEBUG en cada request de matches |
| PT-M02 | Caché sin invalidación activa post-scraping |
| IF-M01 | 91 eventos outbox sin procesar |
| PR-M01 | *(igual que PT-C01)* |

### 🟢 Bajos (8) — No bloquean, deuda técnica

| ID | Descripción |
|----|-------------|
| AU-B01 | Sin refresh token |
| AU-B02 | Rate limiting no activo |
| PR-B01 | `prediction_id` = `request_id` en audit log |
| BT-B01 | BetSlip sin datos para validar end-to-end |
| BT-B02 | Importación no usada en `bet_service.py` |
| PT-B01 | N+1 queries para odds en listado de partidos |
| IF-B01 | Ver AU-M01 |
| IF-B02 | Circuit breaker no protege acceso a Neon |

---

## 7. Fix Inmediato Requerido (PT-C01)

Aplicar antes de arrancar el backend para que `/predict/upcoming` funcione:

```python
# Backend/app/schemas/prediction.py — líneas 31-32
class PredictionResponse(BaseModel):
    game_id: int
    home_team_id: Optional[int] = None   # cambiar de int a Optional[int]
    away_team_id: Optional[int] = None   # cambiar de int a Optional[int]
    home_team_name: str
    away_team_name: str
    ...
```

---

## 8. Cobertura de Requisitos Funcionales

| RF | Descripción | Estado |
|----|-------------|--------|
| RF-01 | Autenticación JWT + argon2 | ✅ |
| RF-02 | Registro con verificación email | ✅ |
| RF-03 | RBAC (admin/operator/client) | ✅ |
| RF-04 | 2FA TOTP | ✅ |
| RF-05 | Circuit Breaker | ✅ (parcial) |
| RF-06 | Idempotencia | ✅ |
| RF-07 | Snapshot de odds por request | ✅ |
| RF-08 | Patrón Outbox | ✅ (worker pendiente) |
| RF-09 | Audit Log | ✅ |
| RF-10 | Predicción ML con modelo real | ✅ |
| RF-11 | Predicción partidos futuros (LiveFeatureExtractor) | ✅ |
| RF-12 | Team-props en predicción | ✅ |
| RF-13 | Implied probability de odds de mercado | ✅ (1.4% cobertura) |
| RF-14 | Liquidación automática de apuestas | ❌ |
| RF-15 | Dashboard con datos reales | ⚠️ (parcial — créditos y matches OK, bets vacío) |

**Cobertura: 13/15 RFs implementados (87%)** — apto para defensa de tesis.

---

*Reporte generado automáticamente — HAW QA Suite v1.0*
