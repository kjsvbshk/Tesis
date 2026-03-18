# Sistema de Predicciones y Apuestas - HAW

Proyecto de tesis que implementa un sistema completo de predicciones deportivas con machine learning aplicado a la NBA. Permite a usuarios registrados visualizar predicciones generadas por modelos ML y realizar apuestas virtuales sobre resultados de partidos.

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         PIPELINE DE DATOS                        │
│                                                                   │
│  ESPN (web)                                                       │
│      │                                                            │
│      ▼                                                            │
│  ┌──────────┐   data/raw   ┌──────┐   Neon (espn)   ┌────────┐  │
│  │Scrapping │ ──────────► │  ETL  │ ──────────────► │  ML    │  │
│  │ Module  │              └──────┘                  │ Module │  │
│  └──────────┘                                       └────────┘  │
│                                                          │        │
│                                                     .joblib       │
│                                                          │        │
└─────────────────────────────────────────────────────────┼────────┘
                                                           │
┌─────────────────────────────────────────────────────────┼────────┐
│                      APLICACIÓN                          │        │
│                                                          ▼        │
│  ┌──────────┐    HTTP/JWT    ┌─────────────────────────────────┐  │
│  │Frontend  │ ◄──────────── │         Backend (FastAPI)        │  │
│  │ (React)  │ ──────────── ► │  Auth | Bets | Predictions      │  │
│  └──────────┘               └─────────────────────────────────┘  │
│                                            │                       │
│                                     Neon (app/sys)                │
└────────────────────────────────────────────────────────────────── ┘
```

### Módulos

| Módulo | Tecnología principal | Responsabilidad |
|--------|---------------------|-----------------|
| **Scrapping** | Python, BeautifulSoup, Selenium | Extrae datos de ESPN y los carga en PostgreSQL |
| **ML** | scikit-learn, XGBoost, pandas | Entrena y exporta modelos de predicción |
| **Backend** | FastAPI, SQLAlchemy | API REST: autenticación, predicciones, apuestas |
| **Frontend** | React 19, TypeScript, Vite | Interfaz de usuario web |

---

## Base de Datos

El sistema usa **Neon PostgreSQL** (cloud) con tres schemas separados:

| Schema | Responsable | Contenido |
|--------|-------------|-----------|
| `espn` | Scrapping | Partidos, estadísticas, lesiones, cuotas (fuente de verdad externa) |
| `ml` | ML | `ml_ready_games` con features engineered listas para entrenamiento |
| `app` / `sys` | Backend | Usuarios, transacciones, apuestas, predicciones, auditoría |

---

## Flujo de Datos Completo

```
1. SCRAPPING (diario)
   ESPN → BeautifulSoup/Selenium → data/raw/ → ETL → Neon (espn schema)
   Tablas: games, team_stats, player_stats, standings, injuries, odds

2. FEATURE ENGINEERING (por demanda)
   Neon (espn) → build_features.py → Neon (ml.ml_ready_games)
   Features: rolling stats, rest days, injury counts, implied probabilities

3. ENTRENAMIENTO (por temporada)
   ml.ml_ready_games → RandomForest + XGBoost → nba_prediction_model_vX.X.X.joblib
   → Backend/ml/models/ + registro en sys.model_versions

4. PREDICCIÓN EN TIEMPO REAL
   Usuario → Frontend → Backend → carga modelo .joblib → predict() → PredictionResponse
   Cache TTL 5 min, snapshot de odds, evento en outbox, registro en auditoría

5. APUESTA VIRTUAL
   Usuario → Frontend → Backend → verifica saldo → registra apuesta → deduce créditos
   Resultado evaluado post-partido → créditos al ganador
```

---

## Inicio Rápido

### Prerequisitos

- Python 3.11+
- Node.js 18+
- Cuenta en Neon (PostgreSQL cloud) — o PostgreSQL local
- Chrome/Chromium (para scrapers con Selenium)

### 1. Configuración de base de datos

Crear un archivo `.env` en la raíz con las credenciales de Neon:

```bash
NEON_DB_HOST=ep-xxx.us-east-1.aws.neon.tech
NEON_DB_PORT=5432
NEON_DB_NAME=neondb
NEON_DB_USER=...
NEON_DB_PASSWORD=...
NEON_DB_SSLMODE=require
NEON_DB_CHANNEL_BINDING=require

DB_SCHEMA=sys
APP_SCHEMA=app
NBA_DB_SCHEMA=espn
ML_DB_SCHEMA=ml

SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

EMAIL_PROVIDER=console
CORS_ORIGINS=http://localhost:5173
```

### 2. Scrapping — poblar base de datos

```bash
cd Scrapping/nba
pip install -r requirements.txt

# Primera carga completa
python -m espn.player_stats_scraper --season "2024-25" --type "regular"
python -m espn.team_stats_scraper --season "2024-25" --type "regular"
python update_injuries_odds.py --load-db
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"
python load_data.py
```

### 3. ML — preparar dataset y entrenar modelo

```bash
cd ML
pip install -r requirements.txt

python scripts/init_ml_schema.py
python scripts/create_ml_ready_games.py
python src/etl/build_features.py
python src/etl/validate_data_quality.py
# Luego entrenar y exportar modelo a Backend/ml/models/
```

### 4. Backend — iniciar API

```bash
cd Backend
pip install -r requirements.txt

python migrations/scripts/create_tables_neon.py
python migrations/init/init_basic_data.py
python migrations/init/init_rbac_data.py

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger UI: http://localhost:8000/docs
```

### 5. Frontend — iniciar interfaz

```bash
cd Frontend
npm install

# Crear .env con:
# VITE_API_BASE_URL=http://localhost:8000/api/v1

npm run dev
# http://localhost:5173
```

---

## Documentación por Módulo

- [Backend/README.md](./Backend/README.md) — API endpoints, arquitectura, seguridad, deployment
- [ML/README.md](./ML/README.md) — Pipeline ML, fases, feature engineering, entrenamiento
- [Scrapping/README.md](./Scrapping/README.md) — Scrapers, ETL, comandos, scheduler
- [Frontend/README.md](./Frontend/README.md) — Componentes, estado, autenticación, deployment

---

## Deployment

| Componente | Plataforma | URL |
|-----------|-----------|-----|
| Backend | Render | `https://tesis-waun.onrender.com` |
| Frontend | Vercel | `https://house-always-win.vercel.app` |
| Base de datos | Neon | Cloud PostgreSQL |

---

## Tecnologías Principales

```
Backend:  Python 3.11 · FastAPI · SQLAlchemy · scikit-learn · XGBoost · Redis (opcional)
ML:       pandas · numpy · scikit-learn · XGBoost · joblib · psycopg2
Scraping: requests · BeautifulSoup · Selenium · APScheduler · psycopg2
Frontend: React 19 · TypeScript · Vite · Zustand · Tailwind CSS · React Router 7
Base BD:  PostgreSQL (Neon) — schemas: espn · ml · app/sys
```

---

## Autores

**Irving Rios Ramirez** · **Jhon Edison Montaño Parra**
Trabajo de Grado — Universidad Manuela Beltrán (UMB), Bogotá, Colombia · 2026

---

## Licencia

El código fuente de este proyecto está licenciado bajo la **MIT License** — ver [`LICENSE`](./LICENSE).
La documentación está licenciada bajo **CC BY 4.0** — ver [`LICENSE-CC`](./LICENSE-CC).
Los avisos de atribución a terceros se encuentran en [`NOTICE.md`](./NOTICE.md).

> Trabajo desarrollado con fines exclusivamente académicos. No involucra dinero real ni fomenta el juego.
