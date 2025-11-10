# Sistema de Extracción de Datos Premier League

## ¿Qué hace este sistema?

Este sistema automatiza la recolección de información de la Premier League desde ESPN. El sistema visita las páginas web de ESPN, extrae la información de partidos y la guarda de forma organizada en archivos y en una base de datos.

## ¿Qué datos extrae el sistema?

El sistema recolecta información sobre partidos de la Premier League:

### 1. **Partidos y Resultados** (`matches`)
   - Información de cada partido: equipos, marcadores, fechas, resultados
   - Datos organizados por temporada
   - Se consolida en un solo registro por partido (eliminando duplicados)

## Estructura del Proyecto

```
premier_league/
├── espn/                    # Extractores de datos de ESPN
│   └── matches_scraper.py    # Extrae resultados de partidos
│
├── etl/                     # Procesamiento y consolidación de datos
│   └── transform_consolidate.py   # Consolida todos los datos en uno solo
│
├── utils/                   # Herramientas compartidas
│   ├── logger.py           # Sistema de registro de actividades
│   └── __init__.py
│
├── data/                    # Datos extraídos
│   ├── raw/                 # Datos sin procesar (CSV)
│   └── processed/           # Datos procesados y consolidados
│
├── logs/                    # Registros de actividades del sistema
│
├── config.yaml              # Configuración del sistema
└── README.md               # Este archivo
```

## Instalación y Configuración

### Requisitos Previos

- Python 3.11 o superior
- PostgreSQL 15 o superior (opcional, para carga a base de datos)
- Playwright (se instala automáticamente con requirements.txt)

### Pasos de Instalación

1. **Instalar las dependencias de Python:**
   ```bash
   cd Scrapping/premier_league
   pip install -r requirements.txt
   ```

2. **Instalar Playwright:**
   ```bash
   playwright install chromium
   ```

3. **Configurar la base de datos (opcional):**
   - Edita el archivo `config.yaml` con tus credenciales de base de datos:
     ```yaml
     DATABASE_URL: postgresql://usuario:contraseña@localhost:5432/nba_data
     DB_SCHEMA: espn
     ```

## Cómo Usar el Sistema

### Scraping de Partidos

#### Scrapear una temporada completa

```bash
# Temporada 2024
python -m espn.matches_scraper --season "2024"

# Temporada 2023
python -m espn.matches_scraper --season "2023"

# Temporada 2022
python -m espn.matches_scraper --season "2022"
```

#### Scrapear un equipo específico

```bash
# Scrapear solo Arsenal
python -m espn.matches_scraper --season "2024" --team "Arsenal"

# Scrapear solo Liverpool
python -m espn.matches_scraper --season "2024" --team "Liverpool"
```

### Consolidar Datos (ETL)

Una vez que tengas los datos scrapeados, puedes consolidarlos en un solo dataset:

```bash
# Ejecutar ETL
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"
```

Este proceso:
- Lee todos los archivos CSV de `data/raw/`
- Consolida partidos duplicados (cada partido aparece 2 veces, una por cada equipo)
- Crea un registro único por partido con `home_team`, `away_team`, `home_score`, `away_score`
- Calcula variables derivadas (`home_win`, `goal_diff`, `total_goals`)
- Guarda el dataset consolidado en `data/processed/premier_league_full_dataset.csv`

## ¿Dónde se Guardan los Datos?

### Archivos Locales

- **Datos sin procesar:** `data/raw/`
  - `premier_league_matches_YYYY.csv` - Resultados de partidos por temporada (CSV)
  - `premier_league_YYYY.csv` - Resultados de partidos (formato alternativo)

- **Datos procesados:** `data/processed/`
  - `premier_league_full_dataset.csv` - Dataset consolidado con todos los datos

### Estructura de Datos

#### Datos Raw (por equipo)
Cada partido aparece 2 veces (una vez por cada equipo):
- `season` - Temporada
- `team_name` - Nombre del equipo
- `team_id` - ID del equipo en ESPN
- `date` - Fecha del partido
- `venue` - "Home" o "Away"
- `opponent` - Equipo oponente
- `goals_for` - Goles a favor del equipo
- `goals_against` - Goles en contra del equipo
- `goal_diff` - Diferencia de goles
- `result` - Resultado: "W" (Win), "L" (Loss), "D" (Draw)
- `status` - Estado del partido (ej: "FT" - Full Time)
- `competition` - Competición (ej: "English Premier League")

#### Datos Procesados (por partido)
Cada partido aparece una sola vez:
- `match_id` - ID único del partido
- `season` - Temporada
- `date` - Fecha del partido
- `home_team` - Equipo local
- `away_team` - Equipo visitante
- `home_score` - Goles del equipo local
- `away_score` - Goles del equipo visitante
- `status` - Estado del partido
- `competition` - Competición
- `home_win` - 1 si gana el equipo local, 0 si no
- `goal_diff` - Diferencia de goles (local - visitante)
- `total_goals` - Total de goles en el partido

## Equipos de Premier League

El sistema puede scrapear datos de los siguientes equipos:

- Arsenal
- Aston Villa
- Brentford
- Brighton & Hove Albion
- Burnley
- Chelsea
- Crystal Palace
- Everton
- Leeds United
- Leicester City
- Liverpool
- Manchester City
- Manchester United
- Newcastle United
- Norwich City
- Southampton
- Tottenham Hotspur
- Watford
- West Ham United
- Wolverhampton Wanderers

## Monitoreo y Logs

El sistema guarda un registro de todas sus actividades en la carpeta `logs/`. Cada vez que el sistema ejecuta una tarea, guarda:
- Qué datos extrajo
- Si hubo algún error
- Cuánto tiempo tardó
- Cuántos registros procesó

Puedes revisar estos logs para ver qué está haciendo el sistema y si hay algún problema.

## Solución de Problemas

### El sistema no puede conectarse a la base de datos
- Verifica que PostgreSQL esté corriendo
- Revisa las credenciales en `config.yaml`
- Asegúrate de que la base de datos exista

### No se pueden extraer datos
- Asegúrate de tener Playwright instalado: `playwright install chromium`
- Verifica tu conexión a internet
- Revisa los logs en `logs/` para ver qué error específico ocurrió

### Los datos no se consolidan correctamente
- Revisa los logs en `logs/` para ver qué error específico ocurrió
- Verifica que los archivos de datos existan en `data/raw/`
- Asegúrate de que los archivos CSV tengan el formato correcto

### Cargar Datos a la Base de Datos

Una vez que tengas los datos consolidados, puedes cargarlos a la base de datos:

```bash
python load_data.py
```

Este script:
1. Analiza automáticamente la estructura de los datos
2. Detecta tipos de datos, primary keys
3. Crea las tablas necesarias en la base de datos
4. Carga todos los datos usando COPY nativo de PostgreSQL
5. Omite duplicados automáticamente
6. Muestra un resumen de lo que se cargó

**Nota:** El script usa una base de datos separada (`premier_league_data`) diferente a la de NBA (`nba_data`).

## Próximos Pasos

Este sistema es parte de un proyecto más grande que incluye:
- Un backend que usa estos datos para hacer predicciones
- Un frontend que muestra las predicciones y permite hacer apuestas virtuales
- Modelos de machine learning que aprenden de estos datos históricos

Los datos extraídos por este sistema alimentan todo el resto del proyecto.
