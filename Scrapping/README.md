# Sistema de Scraping - Guía de Comandos

Este directorio contiene los sistemas de extracción de datos para diferentes ligas deportivas. Actualmente incluye sistemas para **NBA** y **Premier League**.

## Estructura del Proyecto

```
Scrapping/
├── nba/                    # Sistema de scraping para NBA
│   ├── espn/              # Scrapers de ESPN
│   ├── etl/               # Procesamiento de datos
│   ├── data/              # Datos extraídos
│   └── ...
│
└── premier_league/         # Sistema de scraping para Premier League (en desarrollo)
```

---

## 🏀 NBA - Comandos Disponibles

### 📍 Ubicación
Todos los comandos de NBA deben ejecutarse desde el directorio `nba/`:
```bash
cd Scrapping/nba
```

---

### 1. Scraping de Datos

#### 1.1. Scraping Principal (Boxscores)
Ejecuta el scraping de boxscores de juegos individuales:

```bash
# Ejecución manual (scraping inmediato)
python main.py

# Nota: main.py ejecuta un scheduler que corre diariamente a las 3:00 AM
# Para detenerlo, presiona Ctrl+C
```

#### 1.2. Estadísticas de Jugadores
Extrae estadísticas de los top 50 jugadores por categoría:

```bash
# Temporada regular 2023-24
python -m espn.player_stats_scraper --season "2023-24" --type "regular"

# Playoffs 2023-24
python -m espn.player_stats_scraper --season "2023-24" --type "playoffs"

# Temporada regular 2024-25
python -m espn.player_stats_scraper --season "2024-25" --type "regular"

# Playoffs 2024-25
python -m espn.player_stats_scraper --season "2024-25" --type "playoffs"
```

#### 1.3. Estadísticas de Equipos
Extrae estadísticas ofensivas y defensivas de equipos:

```bash
# Temporada regular 2023-24
python -m espn.team_stats_scraper --season "2023-24" --type "regular"

# Playoffs 2023-24
python -m espn.team_stats_scraper --season "2023-24" --type "playoffs"

# Temporada regular 2024-25
python -m espn.team_stats_scraper --season "2024-25" --type "regular"

# Playoffs 2024-25
python -m espn.team_stats_scraper --season "2024-25" --type "playoffs"
```

#### 1.4. Actualizar Injuries y Odds
Actualiza reportes de lesiones y cuotas de apuestas (datos diarios):

```bash
# Actualizar ambos (injuries y odds) - solo archivos
python update_injuries_odds.py

# Actualizar ambos y cargar a la base de datos
python update_injuries_odds.py --load-db

# Actualizar solo reportes de lesiones
python update_injuries_odds.py --injuries

# Actualizar solo cuotas de apuestas
python update_injuries_odds.py --odds

# Actualizar injuries y cargar a la base de datos
python update_injuries_odds.py --injuries --load-db

# Actualizar odds y cargar a la base de datos
python update_injuries_odds.py --odds --load-db
```

**Nota:** Por defecto, `update_injuries_odds.py` solo actualiza los archivos CSV/JSON. Usa `--load-db` para actualizar también la base de datos.

---

### 2. Procesamiento de Datos (ETL)

#### 2.1. Consolidar Datos
Combina todos los datos extraídos en un dataset consolidado:

```bash
# Desde Python
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"

# O importar y usar en un script
from etl.transform_consolidate import consolidate_nba_data
df = consolidate_nba_data()
```

Este proceso:
- Lee boxscores, team_stats y standings
- Calcula variables derivadas (home_win, point_diff, etc.)
- Genera `data/processed/nba_full_dataset.csv`

---

### 3. Carga de Datos a Base de Datos

#### 3.1. Cargar Todos los Datos
Carga todos los datos extraídos a PostgreSQL:

```bash
python load_data.py
```

Este script:
1. Analiza automáticamente la estructura de los datos
2. Detecta tipos de datos, primary keys y foreign keys
3. Crea las tablas necesarias en la base de datos
4. Carga todos los datos usando COPY nativo de PostgreSQL
5. Omite duplicados automáticamente
6. Muestra un resumen de lo que se cargó

**Tablas que se cargan:**
- `games` - Partidos y resultados
- `player_stats` - Estadísticas de jugadores
- `team_stats` - Estadísticas de equipos
- `standings` - Clasificaciones
- `injuries` - Lesiones
- `odds` - Cuotas de apuestas

---

### 4. Flujo de Trabajo Completo

#### Flujo Típico de Actualización Diaria

```bash
# 1. Actualizar injuries y odds (datos que cambian diariamente)
python update_injuries_odds.py --load-db

# 2. Ejecutar scraping de boxscores (si hay juegos nuevos)
python main.py
# (Presionar Ctrl+C después de que termine)

# 3. Si hay nuevos datos, ejecutar ETL
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"

# 4. Cargar todos los datos actualizados a la base de datos
python load_data.py
```

#### Flujo de Scraping Completo (Primera Vez)

```bash
# 1. Scrapear estadísticas de jugadores (4 temporadas)
python -m espn.player_stats_scraper --season "2023-24" --type "regular"
python -m espn.player_stats_scraper --season "2023-24" --type "playoffs"
python -m espn.player_stats_scraper --season "2024-25" --type "regular"
python -m espn.player_stats_scraper --season "2024-25" --type "playoffs"

# 2. Scrapear estadísticas de equipos (4 temporadas)
python -m espn.team_stats_scraper --season "2023-24" --type "regular"
python -m espn.team_stats_scraper --season "2023-24" --type "playoffs"
python -m espn.team_stats_scraper --season "2024-25" --type "regular"
python -m espn.team_stats_scraper --season "2024-25" --type "playoffs"

# 3. Actualizar injuries y odds
python update_injuries_odds.py --load-db

# 4. Ejecutar ETL para consolidar datos
python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"

# 5. Cargar todos los datos a la base de datos
python load_data.py
```

---

## 📋 Resumen de Comandos por Categoría

### Scraping
| Comando | Descripción |
|---------|-------------|
| `python main.py` | Scraping de boxscores (scheduler diario) |
| `python -m espn.player_stats_scraper --season "YYYY-YY" --type "regular\|playoffs"` | Estadísticas de jugadores |
| `python -m espn.team_stats_scraper --season "YYYY-YY" --type "regular\|playoffs"` | Estadísticas de equipos |
| `python update_injuries_odds.py` | Actualizar injuries y odds (solo archivos) |
| `python update_injuries_odds.py --load-db` | Actualizar injuries y odds (archivos + DB) |

### Procesamiento (ETL)
| Comando | Descripción |
|---------|-------------|
| `python -c "from etl.transform_consolidate import run_etl_pipeline; run_etl_pipeline()"` | Consolidar todos los datos |

### Carga de Datos
| Comando | Descripción |
|---------|-------------|
| `python load_data.py` | Cargar todos los datos a PostgreSQL |

---

## 🔧 Configuración

### Requisitos Previos
- Python 3.11 o superior
- PostgreSQL 15 o superior
- Chrome o Chromium (para scraping de estadísticas de jugadores)

### Instalación

1. **Instalar dependencias:**
   ```bash
   cd Scrapping/nba
   pip install -r requirements.txt
   ```

2. **Configurar base de datos:**
   Edita `nba/config.yaml` con tus credenciales:
   ```yaml
   DATABASE_URL: postgresql://usuario:contraseña@localhost:5432/nba_data
   DB_SCHEMA: espn
   ```

---

## 📁 Estructura de Datos

### Archivos Raw (`nba/data/raw/`)
- `boxscores/` - Resultados de partidos (JSON)
- `player_stats/` - Estadísticas de jugadores (CSV)
- `team_stats/` - Estadísticas de equipos (CSV)
- `standings/` - Clasificaciones (CSV)
- `injuries/` - Reportes de lesiones (CSV)
- `odds/` - Cuotas de apuestas (JSON)

### Archivos Procesados (`nba/data/processed/`)
- `nba_full_dataset.csv` - Dataset consolidado con todos los datos

### Base de Datos (PostgreSQL - Esquema `espn`)
- `games` - Partidos y resultados
- `player_stats` - Estadísticas de jugadores
- `team_stats` - Estadísticas de equipos
- `standings` - Clasificaciones
- `injuries` - Lesiones
- `odds` - Cuotas de apuestas

---

## 📝 Notas Importantes

1. **Scraping de Jugadores y Equipos:** Requiere Chrome/Chromium instalado (usa Selenium)

2. **Actualización de Injuries y Odds:** Estos datos cambian diariamente. Usa `update_injuries_odds.py` para mantenerlos actualizados.

3. **Carga de Datos:** El script `load_data.py` detecta automáticamente la estructura de los datos y crea las tablas necesarias. No necesitas crear las tablas manualmente.

4. **Duplicados:** El sistema omite duplicados automáticamente. Puedes ejecutar los scripts múltiples veces sin preocuparte por datos duplicados.

5. **Logs:** Todos los procesos guardan logs en `nba/logs/` para monitoreo y debugging.

---

## 🆘 Solución de Problemas

### Error de conexión a base de datos
- Verifica que PostgreSQL esté corriendo
- Revisa las credenciales en `nba/config.yaml`
- Asegúrate de que la base de datos `nba_data` exista

### Error al scrapear estadísticas de jugadores
- Asegúrate de tener Chrome o Chromium instalado
- ChromeDriver se instala automáticamente, pero verifica que Chrome esté en el PATH

### Los datos no se cargan correctamente
- Revisa los logs en `nba/logs/`
- Verifica que los archivos de datos existan en `nba/data/raw/`
- Asegúrate de que la base de datos tenga espacio suficiente

---

## 📚 Documentación Adicional

- **NBA:** Ver `nba/README.md` para documentación detallada del sistema NBA
- **Premier League:** Ver `premier_league/README.md` (en desarrollo)

---

## 🚀 Próximos Pasos

Este sistema de scraping alimenta:
- Backend que usa estos datos para hacer predicciones
- Frontend que muestra las predicciones y permite hacer apuestas virtuales
- Modelos de machine learning que aprenden de estos datos históricos

