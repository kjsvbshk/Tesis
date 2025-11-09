# NBA Bets Backend

Backend API para predicción de resultados NBA y simulación de apuestas virtuales.

## 🚀 Características

- **FastAPI** - Framework web moderno y rápido
- **PostgreSQL** - Base de datos relacional robusta
- **SQLAlchemy** - ORM para Python
- **JWT Authentication** - Autenticación segura
- **Machine Learning** - Modelos predictivos (RandomForest, XGBoost)
- **Docker** - Contenerización completa

## 📋 Requisitos

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+

## 🛠️ Instalación

### Opción 1: Con Docker (Recomendado)

```bash
# Clonar el repositorio
cd Backend

# Levantar los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f backend
```

### Opción 2: Instalación Local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp env.example .env
# Editar .env con tus configuraciones

# Levantar PostgreSQL (con Docker)
docker-compose up -d postgres

# Ejecutar la aplicación
uvicorn app.main:app --reload
```

## 🌐 Endpoints de la API

### Autenticación
- `POST /api/v1/users/register` - Registrar usuario
- `POST /api/v1/users/login` - Iniciar sesión

### Partidos
- `GET /api/v1/matches/` - Listar partidos
- `GET /api/v1/matches/today` - Partidos de hoy
- `GET /api/v1/matches/upcoming` - Próximos partidos
- `GET /api/v1/matches/{id}` - Detalle de partido

### Apuestas
- `GET /api/v1/bets/` - Mis apuestas
- `POST /api/v1/bets/` - Realizar apuesta
- `GET /api/v1/bets/{id}` - Detalle de apuesta
- `DELETE /api/v1/bets/{id}` - Cancelar apuesta

### Predicciones
- `POST /api/v1/predict/` - Obtener predicción
- `GET /api/v1/predict/upcoming` - Predicciones próximas
- `GET /api/v1/predict/model/status` - Estado del modelo

### Usuarios
- `GET /api/v1/users/me` - Mi perfil
- `PUT /api/v1/users/me` - Actualizar perfil
- `GET /api/v1/users/credits` - Mis créditos

## 📊 Documentación

Una vez que el servidor esté ejecutándose, puedes acceder a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **pgAdmin**: http://localhost:5050 (admin@nbabets.com / admin123)

## 🗄️ Base de Datos

### Modelos Principales

- **Users** - Usuarios del sistema
- **Teams** - Equipos NBA
- **Games** - Partidos NBA
- **Bets** - Apuestas virtuales
- **Transactions** - Historial de transacciones
- **TeamStatsGame** - Estadísticas por partido

### Conexión

```python
# URL de conexión
DATABASE_URL = "postgresql://nba_user:nba_password@localhost:5432/nba_bets_db"
```

## 🤖 Machine Learning

### Modelos Implementados

- **RandomForest** - Clasificación de resultados
- **XGBoost** - Regresión de puntuaciones
- **Stacking Ensemble** - Combinación de modelos

### Características (Features)

- Promedios móviles de rendimiento
- Eficiencia ofensiva/defensiva
- Indicadores de localía y descanso
- Probabilidades implícitas de cuotas

## 🔧 Desarrollo

### Estructura del Proyecto

```
Backend/
├── app/
│   ├── api/v1/endpoints/     # Endpoints de la API
│   ├── core/                 # Configuración y base de datos
│   ├── models/               # Modelos SQLAlchemy
│   ├── schemas/              # Esquemas Pydantic
│   ├── services/             # Lógica de negocio
│   └── main.py              # Aplicación principal
├── ml/                      # Modelos de ML
├── data/                    # Datos (raw/processed)
├── docker-compose.yml       # Configuración Docker
└── requirements.txt         # Dependencias Python
```

### Comandos Útiles

```bash
# Ejecutar tests
pytest

# Formatear código
black .

# Linting
flake8 .

# Ver logs en tiempo real
docker-compose logs -f

# Reiniciar servicios
docker-compose restart

# Detener servicios
docker-compose down
```

## 🚀 Despliegue

### Producción

```bash
# Construir imagen
docker build -t nba-bets-backend .

# Ejecutar en producción
docker run -d -p 8000:8000 --env-file .env nba-bets-backend
```

## 📝 Notas

- El sistema usa créditos virtuales (no dinero real)
- Las predicciones son para fines educativos
- Los modelos ML se entrenan con datos históricos
- La API incluye autenticación JWT
- Soporte completo para CORS

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es parte de una tesis académica.
