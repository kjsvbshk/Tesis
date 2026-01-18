# API de Predicciones y Apuestas Virtuales NBA

## ¿Qué hace este sistema?

Este es el "cerebro" del proyecto. Es una API (interfaz de programación) que proporciona servicios para:

1. **Hacer predicciones** sobre quién ganará los partidos de la NBA usando inteligencia artificial
2. **Gestionar apuestas virtuales** donde los usuarios pueden apostar créditos virtuales (no dinero real) sobre los resultados
3. **Administrar usuarios** y sus cuentas con créditos virtuales
4. **Proporcionar información** sobre partidos, equipos y estadísticas

Piensa en esto como un servidor que recibe peticiones del frontend (la aplicación web que ven los usuarios) y responde con predicciones, información de partidos, resultados de apuestas, etc.

## ¿Cómo funciona el sistema de predicciones?

El sistema usa modelos de machine learning (aprendizaje automático) que han sido entrenados con datos históricos de la NBA. Cuando quieres saber quién ganará un partido, el sistema:

1. **Recopila información** sobre los equipos que van a jugar:
   - Rendimiento reciente de cada equipo
   - Estadísticas ofensivas y defensivas
   - Si juegan en casa o fuera
   - Días de descanso
   - Lesiones de jugadores importantes
   - Cuotas de apuestas (probabilidades)

2. **Analiza los datos** usando los modelos de inteligencia artificial:
   - **RandomForest**: Predice quién ganará (clasificación)
   - **XGBoost**: Predice cuántos puntos anotará cada equipo (regresión)
   - **Stacking Ensemble**: Combina múltiples modelos para mayor precisión

3. **Genera una predicción** con:
   - Probabilidad de victoria de cada equipo
   - Puntuación esperada
   - Nivel de confianza de la predicción

## ¿Qué es el sistema de apuestas virtuales?

Los usuarios pueden hacer apuestas virtuales usando créditos (no dinero real). El sistema:

- **Registra las apuestas** que hace cada usuario
- **Calcula las ganancias** cuando un usuario acierta
- **Mantiene un historial** de todas las apuestas
- **Gestiona los créditos** de cada usuario

Es importante entender que esto es **100% virtual** - no se usa dinero real, solo créditos dentro del sistema para fines educativos y de entretenimiento.

## Estructura del Proyecto

```
Backend/
├── app/
│   ├── api/v1/endpoints/    # Puntos de entrada de la API
│   │   ├── matches.py       # Información de partidos
│   │   ├── bets.py          # Sistema de apuestas
│   │   ├── predictions.py   # Predicciones de IA
│   │   └── users.py         # Gestión de usuarios
│   │
│   ├── core/                # Configuración central
│   │   ├── config.py        # Configuración del sistema
│   │   └── database.py      # Conexión a base de datos
│   │
│   ├── models/              # Estructura de datos en la base de datos
│   │   ├── user.py          # Modelo de usuarios
│   │   ├── game.py          # Modelo de partidos
│   │   ├── bet.py           # Modelo de apuestas
│   │   └── team.py          # Modelo de equipos
│   │
│   ├── schemas/             # Validación de datos
│   │   └── ...              # Esquemas para validar datos entrantes
│   │
│   ├── services/            # Lógica de negocio
│   │   ├── auth_service.py  # Autenticación de usuarios
│   │   ├── bet_service.py   # Lógica de apuestas
│   │   ├── prediction_service.py  # Lógica de predicciones
│   │   └── match_service.py # Lógica de partidos
│   │
│   └── main.py              # Aplicación principal
│
├── ml/                      # Modelos de machine learning
│   └── (modelos entrenados)
│
└── requirements.txt         # Librerías necesarias
```

## Instalación y Configuración

### Requisitos Previos

- Python 3.11 o superior
- PostgreSQL 15 o superior
- Docker y Docker Compose (opcional, pero recomendado)

### Opción 1: Instalación con Docker (Recomendado)

Esta es la forma más fácil de instalar y ejecutar el sistema:

```bash
# Ir a la carpeta del backend
cd Backend

# Levantar todos los servicios (API + Base de datos)
docker-compose up -d

# Ver los logs para verificar que todo funciona
docker-compose logs -f backend
```

El sistema estará disponible en: http://localhost:8000

### Opción 2: Instalación Local

Si prefieres instalar todo manualmente:

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp env.example .env
# Editar .env con tus configuraciones de base de datos

# Levantar PostgreSQL (con Docker)
docker-compose up -d postgres

# Ejecutar la aplicación
uvicorn app.main:app --reload
```

## Cómo Usar la API

### Documentación Interactiva

Una vez que el servidor esté corriendo, puedes acceder a:

- **Swagger UI**: http://localhost:8000/docs
  - Interfaz visual donde puedes probar todos los endpoints
  - Muestra qué datos necesitas enviar y qué respuestas recibirás

- **ReDoc**: http://localhost:8000/redoc
  - Documentación alternativa más legible

### Endpoints Principales

#### Autenticación

**Registrar un nuevo usuario:**
```
POST /api/v1/users/register
Body: {
  "username": "usuario123",
  "email": "usuario@ejemplo.com",
  "password": "contraseña_segura"
}
```

**Iniciar sesión:**
```
POST /api/v1/users/login
Body: {
  "username": "usuario123",
  "password": "contraseña_segura"
}
```
Devuelve un token que necesitas usar para las demás peticiones.

#### Partidos

**Ver todos los partidos:**
```
GET /api/v1/matches/
```

**Ver partidos de hoy:**
```
GET /api/v1/matches/today
```

**Ver próximos partidos:**
```
GET /api/v1/matches/upcoming
```

**Ver detalles de un partido específico:**
```
GET /api/v1/matches/{id}
```

#### Predicciones

**Obtener predicción para un partido:**
```
POST /api/v1/predict/
Body: {
  "game_id": 12345,
  "home_team_id": 1,
  "away_team_id": 2
}
```

**Ver predicciones de próximos partidos:**
```
GET /api/v1/predict/upcoming
```

**Ver estado de los modelos de IA:**
```
GET /api/v1/predict/model/status
```

#### Apuestas

**Ver mis apuestas:**
```
GET /api/v1/bets/
Headers: Authorization: Bearer {tu_token}
```

**Hacer una apuesta:**
```
POST /api/v1/bets/
Headers: Authorization: Bearer {tu_token}
Body: {
  "game_id": 12345,
  "bet_type": "home_win",
  "amount": 100
}
```

**Ver detalles de una apuesta:**
```
GET /api/v1/bets/{id}
Headers: Authorization: Bearer {tu_token}
```

**Cancelar una apuesta:**
```
DELETE /api/v1/bets/{id}
Headers: Authorization: Bearer {tu_token}
```

#### Usuarios

**Ver mi perfil:**
```
GET /api/v1/users/me
Headers: Authorization: Bearer {tu_token}
```

**Actualizar mi perfil:**
```
PUT /api/v1/users/me
Headers: Authorization: Bearer {tu_token}
Body: {
  "email": "nuevo_email@ejemplo.com"
}
```

**Ver mis créditos:**
```
GET /api/v1/users/credits
Headers: Authorization: Bearer {tu_token}
```

## Base de Datos

El sistema usa PostgreSQL para almacenar toda la información. Las tablas principales son:

- **users**: Información de los usuarios registrados
- **teams**: Equipos de la NBA
- **games**: Partidos y resultados
- **bets**: Apuestas realizadas por los usuarios
- **transactions**: Historial de transacciones de créditos
- **team_stats_game**: Estadísticas de equipos por partido

### Conexión a la Base de Datos

La conexión se configura en el archivo `.env`:
```
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/nba_data
```

## Modelos de Machine Learning

El sistema usa varios modelos de inteligencia artificial para hacer predicciones:

### RandomForest
- **Qué hace**: Predice quién ganará el partido (clasificación)
- **Cómo funciona**: Analiza múltiples características de los equipos y vota por el resultado más probable

### XGBoost
- **Qué hace**: Predice cuántos puntos anotará cada equipo (regresión)
- **Cómo funciona**: Usa un algoritmo avanzado que aprende de los datos históricos

### Stacking Ensemble
- **Qué hace**: Combina las predicciones de múltiples modelos
- **Por qué es mejor**: Al combinar varios modelos, las predicciones son más precisas y confiables

### Características que Analizan los Modelos

Los modelos consideran:
- **Rendimiento reciente**: Cómo han jugado los equipos en los últimos partidos
- **Eficiencia ofensiva/defensiva**: Qué tan bien atacan y defienden
- **Ventaja de localía**: Si juegan en casa o fuera
- **Días de descanso**: Si los equipos están descansados o cansados
- **Probabilidades de cuotas**: Lo que dicen las casas de apuestas

## Desarrollo

### Estructura del Código

El código está organizado de forma que cada parte tiene una responsabilidad clara:

- **endpoints/**: Define las rutas de la API y qué hace cada una
- **services/**: Contiene la lógica de negocio (cómo se hacen las predicciones, cómo se procesan las apuestas, etc.)
- **models/**: Define cómo se almacenan los datos en la base de datos
- **schemas/**: Valida que los datos que llegan sean correctos

### Comandos Útiles para Desarrollo

```bash
# Ejecutar tests
pytest

# Formatear el código automáticamente
black .

# Verificar calidad del código
flake8 .

# Ver logs en tiempo real (con Docker)
docker-compose logs -f

# Reiniciar los servicios
docker-compose restart

# Detener los servicios
docker-compose down
```

## Flujo de Trabajo Típico

1. **Usuario se registra** → Se crea una cuenta con créditos iniciales
2. **Usuario ve partidos disponibles** → La API consulta la base de datos
3. **Usuario solicita una predicción** → El sistema usa los modelos de IA para predecir
4. **Usuario hace una apuesta** → Se registra la apuesta y se deducen créditos
5. **Termina el partido** → El sistema verifica si la apuesta fue correcta
6. **Si acertó** → Se le agregan créditos según las probabilidades

## Notas Importantes

- **Créditos virtuales**: Todo el sistema usa créditos virtuales, no dinero real. Es solo para fines educativos y de entretenimiento.

## Deployment en Render

### Configuración Requerida

1. **Root Directory**: `Backend` (sin espacios)
2. **Dockerfile Path**: `Backend/Dockerfile`
3. **Environment Variables**:
   - Variables de base de datos (Neon)
   - `SECRET_KEY`: Clave secreta para JWT
   - `CORS_ORIGINS`: URLs permitidas (ej: `http://localhost:5173,https://tu-frontend.vercel.app`)
   - **Email (SMTP Gmail)**: `EMAIL_PROVIDER=smtp`, `SMTP_USER`, `SMTP_PASSWORD`, etc.
   - **Redis (Opcional)**: `USE_REDIS=true`, `REDIS_URL`

### Servicios de Producción

#### Email Service - SMTP (Gmail)
Configuración requerida:
- `EMAIL_PROVIDER=smtp`
- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=465`
- `SMTP_USER=tu_email@gmail.com`
- `SMTP_PASSWORD=tu_app_password` (ver abajo)
- `SMTP_FROM_EMAIL=tu_email@gmail.com`

**Cómo obtener una App Password de Google:**
1. Ve a https://myaccount.google.com/security
2. Habilita la **verificación en 2 pasos** (si no está habilitada)
3. Ve a **"Contraseñas de aplicaciones"** (App Passwords)
4. Genera una nueva contraseña para **"Correo"**
5. Usa esa contraseña en `SMTP_PASSWORD` (NO uses tu contraseña normal de Gmail)

Para desarrollo local, usa `EMAIL_PROVIDER=console` para ver códigos en los logs.

#### Redis + RQ (Opcional)
Redis es **completamente opcional**. El sistema funciona sin Redis:
- **Caché**: Usa memoria (suficiente para una instancia)
- **Colas**: Usa Outbox Pattern (eventos transaccionales) + RQ con fallback síncrono

**Arquitectura Híbrida:**
- **Outbox Pattern**: Para eventos transaccionales críticos (`bet.placed`, `prediction.completed`)
- **Redis + RQ**: Para tareas asíncronas (emails, sincronización de proveedores, limpieza)

Redis es útil solo si:
- Quieres optimizar colas (más eficiente que polling de BD)
- Tienes múltiples instancias del backend
- Necesitas caché persistente entre reinicios

**Para usar Redis + RQ:**
1. Configurar Redis (ver `REDIS_SETUP.md`)
2. Ejecutar worker: `python -m app.workers.rq_worker` (en proceso separado)
3. Las tareas se encolarán automáticamente

Ver `env.example` y `REDIS_SETUP.md` para más detalles.

## Documentación Adicional

- `API_DOCUMENTATION.md`: Documentación completa de endpoints
- `OPTIMIZATION_NOTES.md`: Notas sobre optimizaciones y mejoras recomendadas
- `REDIS_SETUP.md`: Guía completa para configurar Redis (opcional, solo para producción escalable)

- **Predicciones educativas**: Las predicciones son generadas por modelos de IA entrenados con datos históricos. No son garantía de resultados reales.

- **Autenticación**: El sistema usa JWT (tokens) para autenticar usuarios. Cada petición que requiere autenticación necesita incluir el token en los headers.

- **CORS**: El sistema está configurado para aceptar peticiones desde el frontend en desarrollo (localhost:3000 y localhost:5173).

## Solución de Problemas

### La API no inicia
- Verifica que PostgreSQL esté corriendo
- Revisa las credenciales en el archivo `.env`
- Asegúrate de que el puerto 8000 no esté en uso

### No puedo conectarme a la base de datos
- Verifica que PostgreSQL esté corriendo: `docker-compose ps`
- Revisa los logs: `docker-compose logs postgres`
- Verifica las credenciales en `.env`

### Las predicciones no funcionan
- Verifica que los modelos de ML estén entrenados y disponibles
- Revisa que haya datos en la base de datos
- Consulta los logs para ver errores específicos

## Próximos Pasos

Este backend se conecta con:
- **Frontend**: La aplicación web que usan los usuarios
- **Sistema de Scraping**: Que proporciona los datos históricos para entrenar los modelos

Juntos forman un sistema completo de predicciones y apuestas virtuales NBA.
