# Scrapping — Sistema de Extracción de Datos

Módulo de extracción, transformación y carga (ETL) de datos deportivos desde ESPN hacia PostgreSQL (Neon). Es el primer eslabón del pipeline de datos del sistema.

---

## Posición en el Sistema

```
ESPN (web) → Scrapers → data/raw/ → ETL → data/processed/ → load_data.py → Neon (schema espn)
                                                                                    ↓
                                                                             ML module
                                                                             Backend API
```

---

## Estructura del Proyecto

```
Scrapping/
├── README.md
│
├── nba/                                 # Sistema NBA (activo)
│   ├── main.py                          # Scheduler APScheduler (cron diario 3:00 AM)
│   ├── load_data.py                     # Carga inteligente a PostgreSQL
│   ├── update_injuries_odds.py          # Actualización diaria de lesiones y cuotas
│   ├── config.yaml                      # Credenciales de base de datos
│   ├── requirements.txt
│   │
│   ├── espn/                            # Scrapers por tipo de dato
│   │   ├── espn_scraper.py              # Boxscores de partidos individuales
│   │   ├── espn_schedule_scraper.py     # Calendario de partidos
│   │   ├── player_stats_scraper.py      # Estadísticas de jugadores (Selenium)
│   │   ├── team_stats_scraper.py        # Estadísticas de equipos (Selenium)
│   │   └── injuries_scraper.py          # Reportes de lesiones
│   │
│   ├── etl/
│   │   └── transform_consolidate.py     # Consolida todos los datos en un CSV único
│   │
│   ├── utils/
│   │   └── db.py                        # Utilidades de conexión a PostgreSQL
│   │
│   ├── data/
│   │   ├── raw/
│   │   │   ├── boxscores/               # JSON por partido
│   │   │   ├── player_stats/            # CSV por temporada/tipo
│   │   │   ├── team_stats/              # CSV por temporada/tipo
│   │   │   ├── standings/               # CSV de clasificaciones
│   │   │   ├── injuries/                # CSV de lesiones activas
│   │   │   └── odds/                    # JSON de cuotas
│   │   └── processed/
│   │       └── nba_full_dataset.csv     # Dataset consolidado
│   │
│   └── logs/                            # Logs de ejecución
│
└── premier_league/                      # Sistema Premier League (en desarrollo)
```

---

## Scrapers — Descripción Técnica

### `espn_scraper.py` — Boxscores de Partidos

**Tecnología**: `requests` + `BeautifulSoup`
**Fuente**: Páginas individuales de partidos en ESPN
**Trigger**: Scheduler automático (3:00 AM) o manual

Datos extraídos por partido:
- Fecha, equipos, puntuaciones finales
- Estadísticas de box (puntos, rebotes, asistencias, robos, bloqueos, porcentajes de tiro)
- Cuartos individuales
- Minutos jugados por jugador

Output: archivos JSON en `data/raw/boxscores/`

### `espn_schedule_scraper.py` — Calendario

**Tecnología**: `requests` + `BeautifulSoup`
**Fuente**: Página de calendario ESPN

Datos extraídos:
- `game_id` de ESPN
- Fecha y hora del partido
- Equipos local y visitante
- Estado (scheduled / in_progress / final)

### `player_stats_scraper.py` — Estadísticas de Jugadores

**Tecnología**: `Selenium` + ChromeDriver
**Fuente**: Tablas de estadísticas ESPN (requiere JavaScript)

Extrae top 50 jugadores por categoría:
- Puntos, rebotes, asistencias, robos, bloqueos
- Porcentajes de tiro (FG%, 3P%, FT%)
- Minutos por partido

**Nota**: Requiere Chrome/Chromium instalado en el sistema.

### `team_stats_scraper.py` — Estadísticas de Equipos

**Tecnología**: `Selenium` + ChromeDriver
**Fuente**: Tablas de estadísticas de equipos ESPN

Datos por equipo:
- Estadísticas ofensivas: PPG (puntos por partido), FG%, 3P%, rebotes ofensivos
- Estadísticas defensivas: puntos permitidos, robos, bloqueos
- Neto: diferencial de puntos, pace

### `injuries_scraper.py` — Reportes de Lesiones

**Tecnología**: `requests` + `BeautifulSoup`
**Fuente**: Página de lesiones ESPN

Datos por lesión:
- Jugador y equipo afectado
- Tipo de lesión
- Estado (Out / Questionable / Day-to-Day)
- Fecha estimada de regreso

---

## ETL — Transformación y Consolidación

### `etl/transform_consolidate.py`

Combina todas las fuentes en un único dataset analítico:

```
espn.games + espn.team_stats + espn.standings
        ↓
Calcula variables derivadas:
  - home_win (booleano)
  - point_diff (home_score - away_score)
  - home_rest_days / away_rest_days
  - win_streak por equipo
        ↓
data/processed/nba_full_dataset.csv
```

---

## Carga a Base de Datos

### `load_data.py` — Carga Inteligente

Proceso automatizado que no requiere schema previo:

1. **Detección automática de estructura**: analiza los CSV/JSON y determina tipos de columnas
2. **Creación de tablas**: crea las tablas en Neon si no existen, con tipos correctos
3. **Deduplicación**: detecta registros existentes por primary key y los omite
4. **Carga masiva**: usa `COPY` nativo de PostgreSQL para máximo rendimiento
5. **Reporte**: muestra conteo de registros insertados vs. omitidos por tabla

Tablas que gestiona en el schema `espn`:

| Tabla | Descripción | Frecuencia de actualización |
|-------|-------------|----------------------------|
| `games` | Resultados de partidos | Diaria (post-partido) |
| `player_stats` | Stats de jugadores | Por temporada |
| `team_stats` | Stats de equipos | Por temporada |
| `standings` | Clasificaciones | Diaria |
| `injuries` | Lesiones activas | Diaria |
| `odds` | Cuotas de apuestas | Pre-partido |

---

## Scheduler Automático

`main.py` implementa un daemon con **APScheduler**:

```python
# Configuración del cron
scheduler.add_job(
    scrape_daily_games,
    'cron',
    hour=3,
    minute=0
)
```

Se ejecuta a las **3:00 AM** diariamente para scrapear los boxscores de los partidos del día anterior.

Para ejecutarlo como daemon:
```bash
cd Scrapping/nba
python main.py
# Ctrl+C para detener
```

---

## Flujos de Trabajo

### Primera vez (setup completo)

```bash
cd Scrapping/nba
pip install -r requirements.txt

# 1. Estadísticas de jugadores (requiere Chrome)
python -m espn.player_stats_scraper --season "2023-24" --type "regular"
python -m espn.player_stats_scraper --season "2023-24" --type "playoffs"
python -m espn.player_stats_scraper --season "2024-25" --type "regular"

# 2. Estadísticas de equipos (requiere Chrome)
python -m espn.team_stats_scraper --season "2023-24" --type "regular"
python -m espn.team_stats_scraper --season "2023-24" --type "playoffs"
python -m espn.team_stats_scraper --season "2024-25" --type "regular"

# 3. Lesiones y cuotas
python update_injuries_odds.py --load-db

# 4. ETL — consolidar en CSV
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"

# 5. Cargar todo a Neon
python load_data.py
```

### Actualización diaria

```bash
cd Scrapping/nba

# 1. Datos que cambian diariamente
python update_injuries_odds.py --load-db

# 2. Boxscores de partidos nuevos
python main.py
# (Ctrl+C una vez que termine)

# 3. ETL si hay nuevos datos
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"

# 4. Sincronizar con Neon
python load_data.py
```

### Opciones de `update_injuries_odds.py`

```bash
python update_injuries_odds.py              # Actualiza archivos CSV/JSON solamente
python update_injuries_odds.py --load-db    # Actualiza archivos + carga a BD
python update_injuries_odds.py --injuries   # Solo lesiones
python update_injuries_odds.py --odds       # Solo cuotas
python update_injuries_odds.py --injuries --load-db   # Lesiones + carga a BD
python update_injuries_odds.py --odds --load-db       # Cuotas + carga a BD
```

---

## Referencia de Comandos

### Scraping
| Comando | Descripción |
|---------|-------------|
| `python main.py` | Boxscores — scheduler diario (3 AM) |
| `python -m espn.player_stats_scraper --season "YYYY-YY" --type "regular\|playoffs"` | Stats de jugadores |
| `python -m espn.team_stats_scraper --season "YYYY-YY" --type "regular\|playoffs"` | Stats de equipos |
| `python update_injuries_odds.py [--injuries] [--odds] [--load-db]` | Lesiones y cuotas |

### ETL
| Comando | Descripción |
|---------|-------------|
| `python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"` | Consolidar todos los datos |

### Carga a BD
| Comando | Descripción |
|---------|-------------|
| `python load_data.py` | Cargar todos los datos a Neon (schema espn) |

---

## Configuración

### Requisitos del Sistema

- Python 3.11+
- Chrome o Chromium (para scrapers con Selenium)
- Conexión a internet para acceder a ESPN

### Instalación

```bash
cd Scrapping/nba
pip install -r requirements.txt
```

ChromeDriver se instala automáticamente con `webdriver-manager` (incluido en `requirements.txt`). Solo es necesario tener Chrome instalado.

### Configuración de Base de Datos

Editar `nba/config.yaml`:
```yaml
DATABASE_URL: postgresql://usuario:contraseña@host:5432/nombre_bd
DB_SCHEMA: espn
```

O usar variables de entorno `NEON_*` del `.env` compartido en la raíz del repositorio.

---

## Estructura de los Datos Raw

### Boxscores (JSON)
```json
{
  "game_id": "401585...",
  "date": "2024-01-15",
  "home_team": "LAL",
  "away_team": "GSW",
  "home_score": 112,
  "away_score": 107,
  "quarters": [28, 31, 27, 26],
  "player_stats": [...]
}
```

### Odds (JSON)
```json
{
  "game_id": "401585...",
  "date": "2024-01-15",
  "home_team": "LAL",
  "away_team": "GSW",
  "home_odds": -150,
  "away_odds": +130,
  "over_under": 224.5
}
```

---

## Logs y Monitoreo

Todos los procesos generan logs en `nba/logs/`:
- `scraper_YYYY-MM-DD.log` — actividad del scraper
- `load_data_YYYY-MM-DD.log` — resumen de carga a BD

---

## Solución de Problemas

| Problema | Causa probable | Solución |
|----------|---------------|---------|
| Error de conexión a BD | Credenciales incorrectas | Verificar `config.yaml` o variables `NEON_*` |
| Error en scraper de jugadores | Chrome no encontrado | Instalar Chrome y verificar que esté en PATH |
| Datos no aparecen en Neon | ETL no ejecutado | Correr `run_etl_pipeline()` antes de `load_data.py` |
| Duplicados ignorados en carga | Comportamiento esperado | El sistema deduplica automáticamente |
| Rate limit de ESPN | Demasiadas peticiones | Agregar delays entre requests (`time.sleep`) |

---

## Notas Importantes

1. **Datos públicos**: El scraping utiliza únicamente datos públicos de ESPN disponibles sin autenticación.
2. **Idempotencia**: `load_data.py` puede ejecutarse múltiples veces — los registros ya existentes se omiten automáticamente.
3. **Scheduler vs. manual**: `main.py` inicia un proceso daemon. Para scraping puntual, ejecutar directamente los scripts de cada scraper.
4. **Premier League**: El sistema para Premier League está en desarrollo. La estructura es análoga a NBA.
