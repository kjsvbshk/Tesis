# Sistema de Extracción de Datos NBA

## ¿Qué hace este sistema?

Este sistema automatiza la recolección de información de la NBA desde ESPN. El sistema visita las páginas web de ESPN, extrae la información que necesitamos y la guarda de forma organizada en archivos y en una base de datos PostgreSQL (Neon).

Extrae boxscores, estadísticas de jugadores y equipos, lesiones, cuotas y el calendario de partidos. También incluye scripts para recuperar datos históricos faltantes y auditar la cobertura del dataset.

## ¿Qué datos extrae el sistema?

### 1. **Partidos y Resultados** (`boxscores`)
   - Información detallada de cada partido: equipos, puntuaciones, estadísticas por jugador.
   - Se guarda un archivo JSON por cada partido.

### 2. **Estadísticas de Jugadores** (`player_stats`)
   - Puntos, asistencias, rebotes, bloqueos, robos, porcentajes de tiro.
   - Datos organizados por temporada (Regular y Playoffs).
   - Extrae los top 50 jugadores en cada categoría estadística.

### 3. **Estadísticas de Equipos** (`team_stats`)
   - Rendimiento general: PPG, FG%, 3P%, eficiencia ofensiva y defensiva, diferencial de puntos.
   - Un archivo por cada equipo de la NBA.

### 4. **Clasificaciones** (`standings`)
   - Posición de cada equipo, partidos ganados, perdidos, diferencia de juegos.

### 5. **Lesiones** (`injuries`)
   - Reportes diarios de jugadores lesionados, estado y fecha estimada de regreso.

### 6. **Cuotas de Apuestas** (`odds`)
   - Probabilidades de victoria desde una API externa, actualizadas diariamente.

## Estructura del Proyecto

```
nba/
├── main.py                          # Scheduler APScheduler (cron diario 3:00 AM)
├── load_data.py                     # Carga inteligente a PostgreSQL (Neon)
├── update_injuries_odds.py          # Actualización diaria de lesiones y cuotas
├── config.yaml                      # Configuración de base de datos
├── requirements.txt
│
├── espn/                            # Scrapers por tipo de dato
│   ├── espn_scraper.py              # Boxscores de partidos individuales
│   ├── espn_schedule_scraper.py     # Calendario de partidos
│   ├── player_stats_scraper.py      # Estadísticas de jugadores (Selenium)
│   ├── team_stats_scraper.py        # Estadísticas de equipos (Selenium)
│   ├── team_scraper.py              # Scraper alternativo de equipos
│   ├── standings_scraper.py         # Clasificaciones
│   ├── injuries_scraper.py          # Reportes de lesiones
│   ├── odds_scraper.py              # Cuotas de apuestas
│   ├── populate_all_games.py        # Poblar historial completo de partidos ESPN
│   └── recover_missing_scores.py   # Recuperar scores faltantes desde ESPN
│
├── etl/
│   └── transform_consolidate.py     # Consolida todos los datos en un CSV único
│
├── utils/
│   └── db.py                        # Utilidades de conexión a PostgreSQL
│
├── audit_full_coverage.py           # Auditoria de cobertura del dataset
├── fix_game_id_mapping.py           # Corrección de mapeo de game IDs entre fuentes
├── recover_scores.py                # Recuperar scores faltantes en la BD
├── scrape_missing_2026_boxscores.py # Scrapear boxscores faltantes temporada 2025-26
├── scrape_new_boxscores.py          # Scrapear boxscores nuevos (incremental)
├── inspect_schema.py                # Inspeccionar esquema de tablas en Neon
│
├── data/
│   ├── raw/
│   │   ├── boxscores/               # JSON por partido
│   │   ├── player_stats/            # CSV por temporada/tipo
│   │   ├── team_stats/              # CSV por temporada/tipo
│   │   ├── standings/               # CSV de clasificaciones
│   │   ├── injuries/                # CSV de lesiones activas
│   │   └── odds/                    # JSON de cuotas
│   └── processed/
│       └── nba_full_dataset.csv     # Dataset consolidado
│
└── logs/                            # Logs de ejecución
```

## Instalación y Configuración

### Requisitos Previos

- Python 3.11 o superior
- Chrome o Chromium (para scrapers de jugadores y equipos con Selenium)
- Cuenta en Neon PostgreSQL

### Pasos de Instalación

1. **Instalar las dependencias de Python:**
   ```bash
   cd Scrapping/nba
   pip install -r requirements.txt
   ```
   ChromeDriver se instala automáticamente con `webdriver-manager`.

2. **Configurar la base de datos:**
   Crear un archivo `.env` en la raíz del repositorio con las variables `NEON_*`, o editar `config.yaml`:
   ```yaml
   DATABASE_URL: postgresql://usuario:contraseña@host:5432/nombre_bd
   DB_SCHEMA: espn
   ```

## Cómo Usar el Sistema

### Primera vez — setup completo

```bash
cd Scrapping/nba
pip install -r requirements.txt

# 1. Estadísticas de jugadores (requiere Chrome)
python -m espn.player_stats_scraper --season "2024-25" --type "regular"
python -m espn.player_stats_scraper --season "2023-24" --type "regular"

# 2. Estadísticas de equipos (requiere Chrome)
python -m espn.team_stats_scraper --season "2024-25" --type "regular"
python -m espn.team_stats_scraper --season "2023-24" --type "regular"

# 3. Poblar historial completo de partidos
python espn/populate_all_games.py

# 4. Lesiones y cuotas
python update_injuries_odds.py --load-db

# 5. ETL — consolidar en CSV
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"

# 6. Cargar todo a Neon
python load_data.py
```

### Actualización diaria

```bash
cd Scrapping/nba

# 1. Datos que cambian diariamente
python update_injuries_odds.py --load-db

# 2. Boxscores nuevos (incremental)
python scrape_new_boxscores.py

# 3. ETL si hay nuevos datos
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"

# 4. Sincronizar con Neon
python load_data.py
```

### Scheduler automático (daemon)

`main.py` inicia un proceso daemon con APScheduler que ejecuta el scraping a las **3:00 AM** diariamente:

```bash
python main.py
# Ctrl+C para detener
```

### Recuperar datos históricos faltantes

```bash
# Recuperar scores faltantes en la BD
python recover_scores.py

# Recuperar scores desde ESPN directamente
python espn/recover_missing_scores.py

# Scrapear boxscores faltantes de la temporada 2025-26
python scrape_missing_2026_boxscores.py
```

### Auditoría de cobertura

```bash
# Ver cobertura completa del dataset
python audit_full_coverage.py

# Inspeccionar esquema de tablas en Neon
python inspect_schema.py

# Corregir mapeo de game IDs
python fix_game_id_mapping.py
```

### Opciones de `update_injuries_odds.py`

```bash
python update_injuries_odds.py              # Actualiza archivos CSV/JSON solamente
python update_injuries_odds.py --load-db    # Actualiza archivos + carga a BD
python update_injuries_odds.py --injuries   # Solo lesiones
python update_injuries_odds.py --odds       # Solo cuotas
python update_injuries_odds.py --injuries --load-db
python update_injuries_odds.py --odds --load-db
```

## ¿Dónde se Guardan los Datos?

### Archivos Locales

- **Datos sin procesar:** `data/raw/`
  - `boxscores/` — Resultados de partidos (JSON)
  - `player_stats/` — Estadísticas de jugadores (CSV)
  - `team_stats/` — Estadísticas de equipos (CSV)
  - `standings/` — Clasificaciones (CSV)
  - `injuries/` — Reportes de lesiones (CSV)
  - `odds/` — Cuotas de apuestas (JSON)

- **Datos procesados:** `data/processed/`
  - `nba_full_dataset.csv` — Archivo maestro consolidado

### Base de Datos (Neon — schema `espn`)

| Tabla | Descripción | Frecuencia |
|-------|-------------|-----------|
| `games` | Partidos y resultados | Diaria |
| `player_stats` | Estadísticas de jugadores | Por temporada |
| `team_stats` | Estadísticas de equipos | Por temporada |
| `standings` | Clasificaciones | Diaria |
| `injuries` | Lesiones activas | Diaria |
| `odds` | Cuotas de apuestas | Pre-partido |

## Monitoreo y Logs

El sistema guarda registros en la carpeta `logs/`:
- `scraper_YYYY-MM-DD.log` — actividad del scraper
- `load_data_YYYY-MM-DD.log` — resumen de carga a BD

## Solución de Problemas

| Problema | Causa probable | Solución |
|----------|---------------|---------|
| Error de conexión a BD | Credenciales incorrectas | Verificar `config.yaml` o variables `NEON_*` |
| Error en scraper de jugadores | Chrome no encontrado | Instalar Chrome y verificar que esté en PATH |
| Datos no aparecen en Neon | ETL no ejecutado | Correr `run_etl_pipeline()` antes de `load_data.py` |
| Duplicados ignorados en carga | Comportamiento esperado | El sistema deduplica automáticamente |
| Scores faltantes en BD | Partidos sin boxscore | Ejecutar `recover_scores.py` o `scrape_missing_2026_boxscores.py` |

## Notas Importantes

1. **Datos públicos**: El scraping utiliza únicamente datos públicos de ESPN disponibles sin autenticación.
2. **Idempotencia**: `load_data.py` puede ejecutarse múltiples veces — los registros ya existentes se omiten automáticamente.
3. **Scripts de recuperación**: Los scripts `recover_*.py` y `scrape_missing_*.py` permiten rellenar huecos en el historial sin re-scrapear todo.
4. **Premier League**: El sistema para Premier League está en `Scrapping/premier_league/`. La estructura es análoga a NBA pero en estado de desarrollo inicial.
