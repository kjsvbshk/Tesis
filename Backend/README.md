# Backend — NBA Bets API

API REST construida con **FastAPI** para el sistema de predicciones y apuestas virtuales NBA. Actúa como capa de orquestación entre el frontend, los modelos ML y la base de datos PostgreSQL (Neon).

---

## Arquitectura General

```
┌─────────────┐     HTTPS      ┌──────────────────────────────────────────┐
│  Frontend   │ ─────────────► │             FastAPI App                  │
│  (React)    │ ◄───────────── │                                          │
└─────────────┘   JSON/JWT     │  ┌──────────┐  ┌──────────┐  ┌───────┐  │
                               │  │ Endpoints│  │Services  │  │Models │  │
┌─────────────┐                │  │ (routes) │→ │(business │→ │(ORM)  │  │
│  ML Module  │                │  └──────────┘  │  logic)  │  └───────┘  │
│  (.joblib)  │ ◄── carga ──── │                └──────────┘      │      │
└─────────────┘                │                                   ▼      │
                               │  ┌────────────────────────────────────┐  │
                               │  │     Neon PostgreSQL (Cloud)        │  │
                               │  │  schemas: espn | app/sys | ml      │  │
                               │  └────────────────────────────────────┘  │
                               └──────────────────────────────────────────┘
```

---

## Estructura del Proyecto

```
Backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/          # Rutas HTTP
│   │           ├── admin.py        # Endpoints de administración
│   │           ├── bets.py         # Creación y consulta de apuestas
│   │           ├── health.py       # Health checks (/ready, /live)
│   │           ├── matches.py      # Datos de partidos ESPN
│   │           ├── predictions.py  # Predicciones ML con caché e idempotencia
│   │           ├── users.py        # Auth, registro, perfil
│   │           ├── search.py       # Búsqueda de partidos/equipos
│   │           └── requests.py     # Tracking de requests
│   ├── core/
│   │   ├── config.py               # Settings (lee variables de entorno)
│   │   ├── database.py             # Motores SQLAlchemy (espn, sys, app)
│   │   ├── security.py             # JWT: generación y validación
│   │   ├── authorization.py        # RBAC: verificación de permisos
│   │   └── idempotency.py          # Middleware de deduplicación de requests
│   ├── middleware/
│   │   ├── security_middleware.py  # HTTPS, security headers, host validation
│   │   └── security_monitoring.py  # Rate limiting, detección de brute-force
│   ├── models/                     # Modelos SQLAlchemy (ORM)
│   │   ├── user_accounts.py        # UserAccount, Client, Admin, Operator
│   │   ├── game.py                 # Game (partidos ESPN)
│   │   ├── team.py / team_stats.py # Equipos y estadísticas
│   │   ├── espn_bet.py             # Registro de apuestas
│   │   ├── prediction.py           # Predicciones generadas
│   │   ├── model_version.py        # Versiones de modelos ML
│   │   ├── transaction.py          # Ledger de créditos virtuales
│   │   ├── odds_line.py / odds_snapshot.py  # Cuotas y snapshots
│   │   ├── audit_log.py            # Registro de auditoría
│   │   ├── outbox.py               # Outbox Pattern para eventos
│   │   ├── two_factor.py           # 2FA
│   │   └── role.py / permission.py # RBAC
│   ├── schemas/                    # Schemas Pydantic (validación)
│   │   ├── user.py
│   │   ├── bet.py
│   │   ├── match.py
│   │   ├── prediction.py
│   │   └── provider.py
│   ├── services/                   # Lógica de negocio
│   │   ├── auth_service.py         # Autenticación, generación de tokens
│   │   ├── user_service.py         # Gestión de usuarios
│   │   ├── prediction_service.py   # Carga de modelo ML y generación de predicción
│   │   ├── bet_service.py          # Flujo completo de apuesta
│   │   ├── match_service.py        # Consultas a espn.games
│   │   ├── email_service.py        # SendGrid / SMTP / Console
│   │   ├── cache_service.py        # Caché en memoria con TTL
│   │   ├── redis_cache_service.py  # Caché Redis (opcional)
│   │   ├── two_factor_service.py   # Generación y validación OTP
│   │   ├── role_service.py / permission_service.py  # RBAC
│   │   ├── audit_service.py        # Log de acciones importantes
│   │   ├── circuit_breaker.py      # Patrón circuit breaker
│   │   ├── provider_orchestrator.py # Integración con ESPN
│   │   ├── snapshot_service.py     # Snapshot de odds en cada predicción
│   │   ├── outbox_service.py       # Publicación de eventos (Outbox Pattern)
│   │   ├── idempotency_service.py  # Almacenamiento de respuestas
│   │   ├── queue_service.py        # Tareas asíncronas con RQ
│   │   └── request_service.py      # Tracking del ciclo de vida de requests
│   ├── tasks/                      # Tareas RQ (background jobs)
│   └── main.py                     # Punto de entrada de la aplicación
├── migrations/
│   ├── scripts/                    # Scripts SQL de migración
│   ├── init/                       # Inicialización de datos base
│   └── README.md
├── ml/
│   └── models/                     # Modelos .joblib exportados desde ML/
├── requirements.txt
└── README.md
```

---

## Flujo de Datos

### 1. Autenticación

```
POST /api/v1/users/register
  → Validar datos (Pydantic)
  → Crear usuario en app.user_accounts
  → Enviar email con código OTP (6 dígitos, TTL 15 min)
  → Retornar 201

POST /api/v1/users/verify-email
  → Validar OTP
  → Activar cuenta
  → Asignar créditos iniciales (transacción en app.transactions)

POST /api/v1/users/login
  → Verificar password (bcrypt)
  → Verificar cuenta activa
  → Generar JWT (HS256, TTL configurable)
  → Retornar access_token
```

### 2. Predicción ML

```
GET /api/v1/predictions/game/{game_id}
  → Autenticar usuario (JWT)
  → Crear Request en sys.requests (tracking)
  → Consultar caché (TTL 5 min, stale 10 min)
  │
  ├─ [HIT] Retornar resultado cacheado
  │
  └─ [MISS] PredictionService.get_game_prediction()
       → Cargar datos del partido desde espn.games
       → Cargar modelo .joblib activo desde sys.model_versions
       → Construir vector de features
       → model.predict_proba() → probabilidades
       → Crear snapshot de odds (sys.odds_snapshots)
       → Publicar evento en outbox (sys.outbox)
       → Registrar en audit_log
       → Retornar PredictionResponse
```

### 3. Apuesta

```
POST /api/v1/bets
  → Autenticar usuario
  → Verificar saldo suficiente en app.transactions
  → Verificar que el partido no haya comenzado
  → Registrar apuesta en app.espn_bets (estado: PENDING)
  → Deducir créditos (INSERT en app.transactions)
  → Publicar evento bet.placed en outbox
  → Registrar auditoría
  → Retornar apuesta creada
```

---

## Endpoints de la API

### Autenticación y Usuarios
| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/users/register` | Registrar nuevo usuario | No |
| POST | `/api/v1/users/login` | Iniciar sesión, obtener JWT | No |
| POST | `/api/v1/users/verify-email` | Verificar OTP de email | No |
| GET | `/api/v1/users/me` | Perfil del usuario autenticado | JWT |
| PUT | `/api/v1/users/me` | Actualizar perfil | JWT |
| POST | `/api/v1/users/2fa/enable` | Activar autenticación de dos factores | JWT |

### Partidos
| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/matches` | Listar partidos (paginado, filtros) | JWT |
| GET | `/api/v1/matches/{game_id}` | Detalle de un partido | JWT |
| GET | `/api/v1/matches/upcoming` | Próximos partidos | JWT |

### Predicciones
| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/predictions/` | Predicción con idempotencia | JWT |
| GET | `/api/v1/predictions/game/{game_id}` | Predicción por game_id | JWT |
| GET | `/api/v1/predictions/upcoming` | Predicciones próximos partidos | JWT |
| GET | `/api/v1/predictions/model/status` | Estado del modelo ML activo | No |
| POST | `/api/v1/predictions/retrain` | Re-entrenar modelo | JWT |

### Apuestas
| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/bets` | Crear apuesta | JWT |
| GET | `/api/v1/bets` | Listar apuestas del usuario | JWT |
| GET | `/api/v1/bets/{bet_id}` | Detalle de apuesta | JWT |

### Sistema
| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/health/ready` | Readiness check (DB, modelo) | No |
| GET | `/api/v1/health/live` | Liveness check | No |
| GET | `/api/v1/search` | Búsqueda de partidos/equipos | JWT |

---

## Esquema de Base de Datos

El backend opera sobre tres schemas de Neon PostgreSQL:

### Schema `espn` (datos de scraping — solo lectura)
- `games` — partidos con resultados
- `team_stats` — estadísticas por equipo y temporada
- `player_stats` — estadísticas individuales
- `standings` — clasificaciones
- `injuries` — lesiones activas
- `odds` — cuotas de apuestas

### Schema `app` / `sys` (datos de la aplicación)
- `user_accounts` — usuarios (clientes, admins, operadores)
- `transactions` — ledger de créditos virtuales (inmutable, append-only)
- `espn_bets` — registro de apuestas
- `predictions` — predicciones generadas
- `model_versions` — versiones de modelos ML (is_active para versión en uso)
- `requests` — tracking de ciclo de vida de cada request
- `audit_logs` — registro de acciones importantes
- `outbox` — eventos pendientes de procesamiento (Outbox Pattern)
- `odds_snapshots` — snapshot de cuotas en el momento de cada predicción
- `roles`, `permissions` — RBAC

---

## Seguridad

| Mecanismo | Implementación |
|-----------|----------------|
| Autenticación | JWT HS256, TTL configurable |
| Autorización | RBAC con roles y permisos granulares |
| Transporte | HTTPS forzado en producción (redirect middleware) |
| Headers | HSTS, X-Frame-Options, X-Content-Type-Options, CSP |
| Rate Limiting | 5 intentos fallidos / 15 min por IP |
| Idempotencia | Header `X-Idempotency-Key`, TTL 24h |
| Deduplicación | Outbox Pattern para eventos críticos |
| Auditoría | Log de todas las acciones sensibles |
| Email | Verificación OTP antes de activar cuenta |
| 2FA | TOTP opcional por usuario |

---

## Requisitos Previos

- Python 3.11+
- PostgreSQL (Neon recomendado para producción)
- Redis (opcional — para colas RQ y caché distribuida)

---

## Instalación Local

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp env.example .env
# Editar .env con credenciales de Neon y otras configuraciones

# 4. Crear tablas en la base de datos
python migrations/scripts/create_tables_neon.py

# 5. Inicializar datos base (roles, permisos, usuario admin)
python migrations/init/init_basic_data.py
python migrations/init/init_rbac_data.py

# 6. Ejecutar servidor de desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API quedará disponible en `http://localhost:8000`.
Documentación interactiva (Swagger): `http://localhost:8000/docs`

---

## Variables de Entorno

```bash
# Base de datos (Neon)
NEON_DB_HOST=...
NEON_DB_PORT=5432
NEON_DB_NAME=...
NEON_DB_USER=...
NEON_DB_PASSWORD=...
NEON_DB_SSLMODE=require
NEON_DB_CHANNEL_BINDING=require

# Schemas
DB_SCHEMA=sys           # Schema del sistema
APP_SCHEMA=app          # Schema de la aplicación
NBA_DB_SCHEMA=espn      # Schema con datos ESPN
ML_DB_SCHEMA=ml         # Schema con datos ML

# JWT
SECRET_KEY=...          # Clave secreta (mínimo 32 caracteres)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
CORS_ORIGINS=http://localhost:5173,https://tu-frontend.vercel.app

# Email
EMAIL_PROVIDER=sendgrid         # sendgrid | smtp | console
SENDGRID_API_KEY=SG.xxx...
SENDGRID_FROM_EMAIL=tu@email.com

# Redis (opcional)
USE_REDIS=false
REDIS_URL=redis://localhost:6379/0
```

Para desarrollo local, `EMAIL_PROVIDER=console` imprime los códigos OTP en los logs sin enviar emails reales.

---

## Deployment en Render

1. **Root Directory**: `Backend`
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Configurar todas las variables de entorno en el Dashboard de Render
5. Verificar health check post-deploy:
   ```bash
   curl https://tu-backend.onrender.com/api/v1/health/ready
   ```

**Nota sobre email en Render**: Los puertos SMTP (25, 465, 587) están bloqueados. Usar `EMAIL_PROVIDER=sendgrid` obligatoriamente en producción.

---

## Integración con Modelos ML

El servicio `prediction_service.py` carga el modelo activo desde:
```
Backend/ml/models/nba_prediction_model_{version}.joblib
```

La versión activa se determina consultando la tabla `sys.model_versions` donde `is_active = True`. El flujo de actualización de un modelo es:

1. Entrenar modelo en `ML/`
2. Ejecutar `ML/scripts/deploy_model.py --version vX.X.X --activate` (copia + registra + activa)
3. Reiniciar el Backend para que cargue el nuevo modelo

**Versión activa en producción**: v1.6.0 (Ensemble RF+XGBoost, 21 features, pasa todos los criterios de aceptación).

### `PredictionResponse` — campos retornados

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `home_win_probability` | float | Probabilidad victoria local (0.0–1.0) |
| `away_win_probability` | float | Probabilidad victoria visitante |
| `predicted_home_score` | float | Puntuación esperada equipo local |
| `predicted_away_score` | float | Puntuación esperada equipo visitante |
| `predicted_total` | float | Total puntos esperados |
| `predicted_margin` | float | Margen esperado (home − away) |
| `recommended_bet` | str | `"home"` \| `"away"` \| `"over"` \| `"under"` \| `"none"` |
| `confidence_score` | float | Confianza de la predicción (0.0–1.0) |
| `model_version` | str | Versión del modelo usado |

---

## Comandos de Desarrollo

```bash
# Tests
pytest

# Linter y formato
black app/
flake8 app/

# Ver migraciones disponibles
ls migrations/scripts/
```

---

## Notas de Diseño

- **Créditos virtuales**: El sistema no maneja dinero real. Los créditos son un mecanismo de juego para fines educativos.
- **Outbox Pattern**: Garantiza que los eventos (`bet.placed`, `prediction.completed`) no se pierdan incluso si hay fallos de red, usando una tabla transaccional en la misma BD.
- **Idempotencia**: Todas las operaciones críticas aceptan un header `X-Idempotency-Key` para prevenir duplicados en caso de reintentos del cliente.
- **Multi-schema**: Separación clara entre datos de scraping (`espn`), aplicación (`app`/`sys`) y ML (`ml`), permitiendo que cada módulo evolucione independientemente.
