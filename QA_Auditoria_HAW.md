# QA Auditoría — Sistema HAW (House Always Wins)
**Fecha:** 2026-07-20 | **Versión auditada:** v3.1.0 (modelo activo, 52 features) | **Auditor:** QA Engineer (automatizado)
**Auditoría previa:** 2026-06-04 (v2.2.0) — los IDs de hallazgos se conservan para trazabilidad.

---

## Resumen Ejecutivo

| Área | Estado | Críticos | Medios | Bajos |
|------|--------|----------|--------|-------|
| Autenticación y seguridad | ✅ PASA | 0 | 1 | 2 |
| Predicciones ML | ✅ PASA | 0 | 0 | 2 |
| Apuestas y créditos | ⚠️ OBSERVACIONES | 0 | 1 | 3 |
| Partidos y odds | ⚠️ OBSERVACIONES | 0 | 2 | 1 |
| Infraestructura / patrones | ✅ PASA | 0 | 1 | 2 |

**Total: 0 críticos · 5 medios · 10 bajos** (junio: 1 crítico · 9 medios · 8 bajos)

### Evolución desde la auditoría de junio (v2.2.0)

| Hallazgo junio | Estado hoy |
|----------------|-----------|
| 🔴 PT-C01 `home_team_id: int` NOT NULL rompía `/predict/upcoming` | ✅ RESUELTO — `Optional[int] = None` (`schemas/prediction.py:31-32`) |
| 🟡 AU-B02 Rate limiting no activo | ✅ RESUELTO — `check_rate_limit`/`track_failed_login` activos en login y cambio de contraseña |
| 🟡 PR-M03 `inference_latency_ms` no visualizada | ✅ RESUELTO — `PredictionsPage.tsx:293-296` la muestra |
| 🟡 PR-M02 Solo input manual de game_id | ⬇️ BAJO — auto-trigger vía URL `?game_id` desde UpcomingGames implementado; input manual sigue siendo el flujo directo |
| 🟡 BT-M02 Tablas paralelas `espn.bets` / `app.bets` | ⬇️ BAJO — el modelo SQLAlchemy unificó a `espn.bets`; la tabla `app.bets` persiste vacía en la BD (dropear o documentar) |
| 🟡 IF-M01 Outbox worker no corría | 🔄 MEJORADO — `start_outbox_worker()` se lanza en el startup (`main.py:208-209`); verificar filas `published_at IS NULL` en Neon |
| 🟡 BT-M01 Sin liquidación de apuestas | 🔄 PARCIAL — `BetService.settle_bet(bet_id, won)` implementado con abono y reversa; **sin invocadores** (ni worker ni endpoint) |
| 🟡 AU-M01 `datetime.utcnow()` deprecado | ❌ VIGENTE y creció: 49 ocurrencias en 18 archivos (junio: 33/12) |
| 🟡 PT-M01 Prints DEBUG en match_service | ❌ VIGENTE — 26 `print(` en `match_service.py` |
| 🟢 PT-B01 N+1 queries de odds | ❌ VIGENTE |
| 🟢 IF-B02 Circuit breaker solo en providers | ❌ VIGENTE — único uso: `provider_orchestrator.py` |

### Correcciones de seguridad aplicadas 2026-07 (nuevos casos PASS)

Detalle completo en `Backend/README_SECURITY.md`:
- OTP eliminado de las respuestas HTTP de `/forgot-password` y `/send-verification-code` (era account-takeover).
- `echo=False` fijo en SQLAlchemy (antes volcaba SQL con parámetros con `DEBUG=True`).
- 500 genéricos + tracebacks saneados con `scrub_sensitive_text()` en los 10 handlers de flujos con credenciales.
- OTP nunca en logs salvo `EMAIL_PROVIDER=console` explícito.
- Referencias al schema inexistente `sys` corregidas a `app` en scripts ML, configs y mensajes.

---

## 1. Autenticación y Gestión de Usuarios

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| AU-01 | Registro con email válido + verificación OTP | ✅ PASA | `EmailService` + `email_verification_codes`; código solo por email |
| AU-02 | Login con JWT Bearer (HS256) | ✅ PASA | `create_access_token`, hash **Argon2** |
| AU-03 | Token expirado devuelve 401 | ✅ PASA | `verify_token` usa `JWTError` |
| AU-04 | Usuario inactivo bloqueado | ✅ PASA | `is_active` en `get_current_user` |
| AU-05 | 2FA TOTP con QR + backup codes | ✅ PASA | `pyotp`, backup codes SHA-256, header `X-Requires-2FA` |
| AU-06 | RBAC admin/operator/user | ✅ PASA | `require_permission`, permisos granulares scope:acción |
| AU-07 | Sesiones y revocación | ✅ PASA | `user_sessions` con token_hash |
| AU-08 | Recuperación de contraseña | ✅ PASA | OTP 6 dígitos / 15 min, sin eco en respuesta |
| AU-09 | Headers de seguridad HTTP | ✅ PASA | HSTS, X-Frame-Options, CSP; HTTPS redirect; TrustedHost |
| AU-10 | Sin credenciales en logs/respuestas | ✅ PASA | `scrub_sensitive_text` + 500 genéricos + echo SQL off |
| AU-11 | Rate limiting por IP en login | ✅ PASA | `check_rate_limit` → 429 con minutos restantes |

### Hallazgos

**[MEDIO] AU-M01 — `datetime.utcnow()` deprecado (49 ocurrencias / 18 archivos)**
Python 3.13 en uso; reemplazar por `datetime.now(timezone.utc)`. Creció desde junio (33/12) — incluir en definition of done de nuevos PRs.

**[BAJO] AU-B01 — Sin refresh token** (sin cambios; UX de sesión corta, no es riesgo).

**[BAJO] AU-B03 — 28 handlers restantes devuelven `str(e)` al cliente** *(nuevo)*
Los 10 flujos con credenciales ya están saneados; quedan endpoints sin datos sensibles en payload (créditos, listados, permisos, deactivate) que aún exponen detalle interno en el 500. Aplicar el mismo patrón (`logger.error` + scrub + detail genérico).

---

## 2. Predicciones ML

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| PR-01 | Predicción de partido histórico | ✅ PASA | `FeatureExtractor` + `predict_full_robust` |
| PR-02 | Predicción de partido futuro | ✅ PASA | `LiveFeatureExtractor` con fallback si faltan columnas V3.1 |
| PR-03 | 422 cuando el partido no tiene features | ✅ PASA | `FeaturesNotAvailableError` → HTTP 422 |
| PR-04 | 503 cuando el modelo no está cargado | ✅ PASA | `ModelNotLoadedError` → HTTP 503 |
| PR-05 | Detección de feature_set 21/33/35/47/49/50/52 | ✅ PASA | `detect_feature_set` — v3.1.0 → `v3_1_odds` (52) |
| PR-06 | Idempotencia con X-Idempotency-Key | ✅ PASA | `check_idempotency_and_register` |
| PR-07 | Team-props (reb/ast/stl/blk/to) | ✅ PASA | `NBAStatRegressor` × 10 |
| PR-08 | Upcoming games con predicciones | ✅ PASA | PT-C01 resuelto; auto-trigger `?game_id` |
| PR-09 | Caché TTL 5 min + stale | ✅ PASA | `cache_service.get_or_set` |
| PR-10 | Telemetría de latencia visualizada | ✅ PASA | `inference_latency_ms` en dashboard |
| PR-11 | FG%/3P%/FT% rolling como inputs (§2.3.1) | ✅ PASA | `fg_pct_rolling_diff` + 2 en ETL→train→inferencia |
| PR-12 | `implied_prob_*` activas en producción (§2.3.4) | ✅ PASA | default `--use-odds`; pre-imputación por mediana |

### Hallazgos

**[BAJO] PR-B01 — `prediction_id` = `request_id` en audit log** (sin cambios; semántico).

**[BAJO] PR-B02 — Cobertura de cuotas ~1.3 %** *(reclasificado)*
`implied_prob_*` operan pero con señal débil: 53/3975 partidos con cuotas reales. Ampliar histórico de odds para que la feature aporte.

---

## 3. Apuestas y Créditos

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| BT-01 | Colocar apuesta moneyline | ✅ PASA | `BetService.place_bet` |
| BT-02 | Validar créditos suficientes | ✅ PASA | `deduct_credits` + `CheckConstraint credits >= 0` |
| BT-03 | Refund si falla post-débito | ✅ PASA | `add_credits` en except |
| BT-04 | Cancelar apuesta pendiente | ✅ PASA | `cancel_bet` |
| BT-05 | Historial con filtros | ✅ PASA | `get_user_bets` |
| BT-06 | Ledger en `app.transactions` | ✅ PASA | `balance_before/after` |
| BT-07 | Equipo pertenece al partido | ✅ PASA | Cross-check espn.teams/games |
| BT-08 | Estadísticas del usuario | ✅ PASA | `/bets/stats/summary` |
| BT-09 | Liquidación de apuestas | ⚠️ PARCIAL | `settle_bet()` implementado, sin invocadores |
| BT-10 | Over/under | ✅ PASA | `BetType.over_under` |

### Hallazgos

**[MEDIO] BT-M01 — Liquidación implementada pero no conectada**
`BetService.settle_bet(bet_id, won)` liquida con abono de ganancias y reversa ante fallo, pero ningún worker ni endpoint lo invoca. Fix mínimo: endpoint admin `POST /bets/{id}/settle` o job que cruce `espn.bets.status='pending'` contra resultados de `espn.games`.

**[BAJO] BT-B01 — Validación end-to-end del BetSlip pendiente de datos** (sin cambios).
**[BAJO] BT-B02 — Import `get_espn_db` sin uso en `bet_service.py`** (sin cambios).
**[BAJO] BT-B03 — Tabla `app.bets` vacía persiste en la BD** *(reclasificado desde BT-M02)* — el código ya usa solo `espn.bets`; dropear `app.bets` o documentarla como legacy.

---

## 4. Partidos y Odds

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| PT-01..04 | Listados, hoy, por ID, próximos | ✅ PASA | Sin cambios |
| PT-05 | Odds en respuesta | ⚠️ PARCIAL | 53 partidos con odds (~1.3 %) |
| PT-06 | `game_date` en respuesta | ✅ PASA | Verificado |
| PT-07 | Pipeline odds → implied_prob | ✅ PASA | Autodetección de formato + sin vig |
| PT-08 | Filtro partidos futuros | ✅ PASA | PT-C01 resuelto |

### Hallazgos

**[MEDIO] PT-M01 — 26 `print(` de debug en `match_service.py`** — vigente; migrar a `logger.debug`.
**[MEDIO] PT-M02 — Caché sin invalidación post-scraping** — vigente; invalidar al final del ETL o exponer endpoint admin de flush.
**[BAJO] PT-B01 — N+1 queries de odds en listados** — vigente; JOIN en la query principal.

---

## 5. Infraestructura y Patrones

| ID | Caso | Resultado | Notas |
|----|------|-----------|-------|
| IF-01 | Patrón Outbox | ✅ PASA | Worker arranca en startup (`main.py:208`) |
| IF-02 | Audit Log | ✅ PASA | `app.audit_log` |
| IF-03 | Idempotencia | ✅ PASA | Header `X-Idempotency-Key` |
| IF-04 | Circuit Breaker | ✅ PASA | Solo providers (ver IF-B02) |
| IF-05 | HTTPS + security headers | ✅ PASA | |
| IF-06 | Caché TTL + stale-while-revalidate | ✅ PASA | Redis con fallback a memoria |
| IF-07 | Worker outbox publica | ⚠️ VERIFICAR | Revisar `published_at IS NULL` en Neon tras el arranque |
| IF-08 | Health check | ✅ PASA | `/health` |
| IF-09 | Separación de schemas | ✅ PASA | Schemas reales: `app`, `espn`, `ml`, `premier_league` (el schema `sys` no existe; referencias corregidas 2026-07) |
| IF-10 | UNIQUE constraints críticos | ✅ PASA | `uq_player_boxscore` |

### Hallazgos

**[MEDIO] IF-M01 — Publicación del outbox sin verificación en producción**
El worker ya arranca en startup; falta evidencia de procesamiento en Render. Verificar: `SELECT COUNT(*) FROM app.outbox WHERE published_at IS NULL;`

**[BAJO] IF-B01 — Ver AU-M01 (utcnow).**
**[BAJO] IF-B02 — Circuit breaker no cubre Neon ni carga del modelo** — vigente.

---

## 6. Cobertura de Requisitos Funcionales

| RF | Descripción | Junio | Hoy |
|----|-------------|-------|-----|
| RF-01..04 | JWT+Argon2, registro, RBAC, 2FA TOTP | ✅ | ✅ |
| RF-05 | Circuit Breaker | ✅ parcial | ✅ parcial |
| RF-06..07 | Idempotencia, snapshot de odds | ✅ | ✅ |
| RF-08 | Outbox | ✅ worker pendiente | ✅ worker en startup |
| RF-09..12 | Audit, predicción real, live, team-props | ✅ | ✅ |
| RF-13 | Implied probability de mercado | ✅ (no en modelo activo) | ✅ **activa en v3.1.0** |
| RF-14 | Liquidación automática | ❌ | ⚠️ lógica lista, sin invocador |
| RF-15 | Dashboard con datos reales | ⚠️ | ⚠️ (bets aún sin volumen) |

**Cobertura: 13/15 completos + 2 parciales — apto para defensa de tesis.**

---

## 7. Cómo regenerar esta auditoría

Esta auditoría es estática (revisión de código + verificaciones puntuales). Para regenerarla tras cambios:

1. **Actualizar encabezado**: fecha, versión del modelo activo (`SELECT version FROM app.model_versions WHERE is_active;` o el log de startup del backend).
2. **Re-verificar hallazgos vigentes** (comandos desde la raíz del repo, PowerShell usa `findstr` o instalar ripgrep):
   ```bash
   # AU-M01 — utcnow deprecado (objetivo: 0)
   grep -rn "datetime.utcnow()" Backend/app --include="*.py" | wc -l
   # AU-B03 — str(e) expuesto al cliente (objetivo: 0)
   grep -c "str(e)" Backend/app/api/v1/endpoints/users.py
   # PT-M01 — prints de debug (objetivo: 0)
   grep -c "print(" Backend/app/services/match_service.py
   # BT-M01 — invocadores de settle_bet (objetivo: >=1)
   grep -rn "settle_bet" Backend/app --include="*.py" | grep -v "def settle_bet"
   # Fugas de credenciales (objetivo: vacío)
   grep -rn '"code": code\|echo=settings.DEBUG' Backend/app --include="*.py"
   # Schema sys fantasma (objetivo: vacío)
   grep -rn "sys\.model_versions\|get_schema(\"sys\")" Backend ML --include="*.py"
   ```
3. **Pruebas manuales de humo**: registro→OTP por email→login→2FA; predicción de partido histórico y futuro; apuesta con créditos; revisar consola del backend durante un login fallido (sin contraseñas, sin SQL).
4. **Métricas del modelo**: copiar de `ML/models/metadata/v{X}_metadata.json` (campo `metrics`).
5. **Actualizar** las tablas de evolución (sección Resumen) marcando RESUELTO/VIGENTE con evidencia archivo:línea, y recalcular el conteo por severidad.

> Sugerencia: pedir la regeneración a un agente con acceso al repo usando este documento como plantilla — los IDs estables (AU-*, PR-*, BT-*, PT-*, IF-*) permiten comparar auditorías entre versiones.

---

*Reporte regenerado 2026-07-20 — HAW QA Suite v1.1 (base: auditoría 2026-06-04 sobre v2.2.0)*
