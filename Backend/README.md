# NBA Bets API

FastAPI backend para sistema de apuestas deportivas con ML predictions.

## Características Principales

- **Autenticación JWT**: Sistema seguro de autenticación
- **RBAC (Role-Based Access Control)**: Permisos granulares por roles
- **Sistema de Créditos Virtuales**: Moneda virtual para apuestas
- **Predicciones ML**: Integración con modelos de machine learning
- **Proveedores Externos**: Integración con ESPN para datos de partidos
- **Circuit Breaker**: Protección contra fallos en servicios externos
- **Email Verification**: Verificación de correo con códigos
- **Audit Logging**: Registro de acciones importantes
- **Idempotency**: Prevención de duplicación de requests

## Estructura del Proyecto

```
Backend/
├── app/
│   ├── api/v1/endpoints/    # Endpoints de la API
│   ├── core/                 # Configuración, base de datos, autorización
│   ├── models/               # Modelos SQLAlchemy
│   ├── schemas/              # Schemas Pydantic
│   ├── services/             # Lógica de negocio
│   ├── tasks/                # Tareas asíncronas (RQ)
│   └── workers/              # Workers (Outbox, RQ)
├── migrations/               # Scripts SQL de migración
├── requirements.txt          # Dependencias Python
└── README.md                 # Este archivo
```

## Requisitos Previos

- Python 3.11+
- PostgreSQL (Neon recomendado)
- Redis (opcional, para colas RQ)

## Instalación Local

1. **Clonar repositorio** (si aplica)
2. **Crear entorno virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate  # Windows
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**:
   - Copiar `env.example` a `.env`
   - Configurar todas las variables necesarias (ver abajo)

5. **Crear tablas de base de datos**:
   ```bash
   python migrations/scripts/create_tables_neon.py
   ```

6. **Inicializar datos básicos** (opcional):
   ```bash
   python migrations/init/init_basic_data.py
   python migrations/init/init_rbac_data.py
   ```
   
   📖 Ver `migrations/README.md` para más detalles sobre migraciones e inicialización.

7. **Ejecutar servidor**:
   ```bash
   python run.py
   # o
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Configuración

### Variables de Entorno

El archivo `.env` debe contener:

1. **Database Configuration** (Neon):
   - `NEON_DB_HOST`, `NEON_DB_PORT`, `NEON_DB_NAME`
   - `NEON_DB_USER`, `NEON_DB_PASSWORD`

2. **JWT Configuration**:
   - `SECRET_KEY`: Clave secreta para JWT
   - `ALGORITHM`: Algoritmo (HS256)
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: Tiempo de expiración

3. **API Configuration**:
   - `CORS_ORIGINS`: URLs permitidas (ej: `http://localhost:5173,https://tu-frontend.vercel.app`)

4. **Email Configuration** (SendGrid recomendado):
   - `EMAIL_PROVIDER=sendgrid` (o `console` para desarrollo)
   - `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`

5. **Redis Configuration** (Opcional):
   - `USE_REDIS=true`, `REDIS_URL`

### Servicios de Producción

#### Email Service - SendGrid (Recomendado)

**⚠️ IMPORTANTE**: Render y la mayoría de PaaS bloquean puertos SMTP (25, 465, 587). **Debes usar SendGrid** para producción.

**Configuración en SendGrid:**

1. **Crear cuenta en SendGrid**:
   - Ve a https://sendgrid.com
   - Regístrate (plan gratuito disponible: 100 emails/día)

2. **Crear API Key**:
   - Dashboard → Settings → API Keys
   - Click "Create API Key"
   - Nombre: `NBA Bets API` (o el que prefieras)
   - Permisos: **"Full Access"** (o al menos "Mail Send")
   - Click "Create & View"
   - **¡IMPORTANTE!** Copia la API Key inmediatamente (solo se muestra una vez)
   - Guárdala en `SENDGRID_API_KEY` en Render

3. **Verificar Remitente (Sender)**:
   - Dashboard → Settings → Sender Authentication
   - Click "Verify a Single Sender"
   - Completa el formulario:
     - **From Email**: `whousealways@gmail.com` (tu email)
     - **From Name**: `House Always Win`
     - **Reply To**: `whousealways@gmail.com`
     - **Address**: Tu dirección física (para cumplimiento)
     - **City, State, Country**: Tu ubicación
   - Acepta términos y haz click "Create"
   - **Verifica tu email**: SendGrid enviará un email de verificación
   - Abre el email y haz click en el link de verificación
   - Una vez verificado, usa ese email en `SENDGRID_FROM_EMAIL`

**Variables de entorno en Render:**

```bash
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=whousealways@gmail.com
```

**Nota**: El formato de API Key es `SG.` seguido de muchos caracteres. Es muy largo, asegúrate de copiarlo completo.

#### SMTP (Solo para desarrollo local)

**NO funciona en Render** - Solo para pruebas locales:

```bash
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
SMTP_FROM_EMAIL=tu_email@gmail.com
SMTP_USE_TLS=true
```

#### Console Mode (Desarrollo)

Para ver códigos en logs sin enviar emails:

```bash
EMAIL_PROVIDER=console
```

#### Redis + RQ (Opcional)

Redis es **completamente opcional**. El sistema funciona sin Redis:
- **Caché**: Usa memoria (suficiente para una instancia)
- **Colas**: Usa Outbox Pattern (eventos transaccionales) + RQ con fallback síncrono

**Arquitectura Híbrida:**
- **Outbox Pattern**: Para eventos transaccionales críticos (`bet.placed`, `prediction.completed`)
- **Redis + RQ**: Para tareas asíncronas (emails, sincronización de proveedores, limpieza)

Redis es útil solo si:
- Tienes múltiples instancias del backend
- Necesitas colas de tareas en producción
- Requieres caché persistente entre reinicios

## Deployment en Render

### Configuración Requerida

1. **Root Directory**: `Backend` (sin espacios)
2. **Dockerfile Path**: `Backend/Dockerfile`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Environment Variables

Configura estas variables en Render Dashboard:

**Base de Datos (Neon)**:
- `NEON_DB_HOST`, `NEON_DB_PORT`, `NEON_DB_NAME`
- `NEON_DB_USER`, `NEON_DB_PASSWORD`
- `NEON_DB_SSLMODE=require`, `NEON_DB_CHANNEL_BINDING=require`

**JWT**:
- `SECRET_KEY` (genera una clave segura)
- `ALGORITHM=HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES=1440`

**API**:
- `CORS_ORIGINS`: URLs del frontend (ej: `https://house-always-win.vercel.app`)

**Email (SendGrid - REQUERIDO para producción)**:
- `EMAIL_PROVIDER=sendgrid`
- `SENDGRID_API_KEY`: Tu API Key de SendGrid
- `SENDGRID_FROM_EMAIL`: Email verificado en SendGrid (ej: `whousealways@gmail.com`)

**Redis (Opcional)**:
- `USE_REDIS=true`
- `REDIS_URL`: URL completa de Redis (si usas Redis en Render)

### Después del Deploy

1. **Ejecutar migraciones** (si aplica):
   ```bash
   python migrations/scripts/run_migrations.py
   ```

2. **Verificar health check**:
   ```bash
   curl https://tu-backend.onrender.com/api/v1/health/ready
   ```

## Uso de la API

### Endpoints Principales

- `POST /api/v1/users/register` - Registro de usuarios
- `POST /api/v1/users/login` - Iniciar sesión
- `GET /api/v1/users/me` - Obtener usuario actual
- `GET /api/v1/matches` - Listar partidos
- `POST /api/v1/bets` - Crear apuesta
- `GET /api/v1/bets` - Listar mis apuestas
- `GET /api/v1/predictions` - Obtener predicciones ML

### Autenticación

La mayoría de endpoints requieren autenticación JWT:

```bash
# Login
curl -X POST https://tu-api/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"username": "usuario", "password": "contraseña"}'

# Usar token
curl -X GET https://tu-api/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```

## Desarrollo

### Ejecutar Tests

```bash
pytest
```

### Ejecutar Linter

```bash
black app/
flake8 app/
```

## Flujo de Datos

1. **Usuario se registra** → Código de verificación enviado por email
2. **Usuario verifica código** → Cuenta activada
3. **Usuario recibe créditos iniciales** → Puede hacer apuestas
4. **Usuario hace una apuesta** → Se registra la apuesta y se deducen créditos
5. **Termina el partido** → El sistema verifica si la apuesta fue correcta
6. **Si acertó** → Se le agregan créditos según las probabilidades

## Notas Importantes

- **Créditos virtuales**: Todo el sistema usa créditos virtuales, no dinero real. Es solo para fines educativos y de entretenimiento.
