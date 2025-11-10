# Sistema de Extracción de Datos NBA

## ¿Qué hace este sistema?

Este sistema automatiza la recolección de información de la NBA desde ESPN. En lugar de copiar datos manualmente, el sistema visita las páginas web de ESPN, extrae la información que necesitamos y la guarda de forma organizada en archivos y en una base de datos.

Imagina que necesitas información sobre todos los partidos de la NBA, las estadísticas de cada jugador, los equipos, las lesiones, las cuotas de apuestas, etc. Este sistema hace todo eso automáticamente, todos los días, sin que tengas que hacer nada.

## ¿Qué datos extrae el sistema?

El sistema recolecta varios tipos de información:

### 1. **Partidos y Resultados** (`boxscores`)
   - Información detallada de cada partido: quién jugó, cuántos puntos anotó cada jugador, qué equipos ganaron, etc.
   - Se guarda un archivo por cada partido con toda la información del juego.

### 2. **Estadísticas de Jugadores** (`player_stats`)
   - Puntos, asistencias, rebotes, bloqueos, robos, triples anotados por cada jugador.
   - Datos organizados por temporada (Regular y Playoffs).
   - Extrae los top 50 jugadores en cada categoría estadística.

### 3. **Estadísticas de Equipos** (`team_stats`)
   - Rendimiento general de cada equipo: porcentaje de victorias, puntos promedio, eficiencia ofensiva y defensiva.
   - Un archivo por cada equipo de la NBA.

### 4. **Clasificaciones** (`standings`)
   - Posición de cada equipo en la tabla de clasificación.
   - Partidos ganados, perdidos, diferencia de juegos, etc.
   - Datos por temporada.

### 5. **Lesiones** (`injuries`)
   - Reportes diarios de jugadores lesionados.
   - Estado de cada lesión y cuándo se espera que el jugador regrese.

### 6. **Cuotas de Apuestas** (`odds`)
   - Probabilidades de victoria de cada equipo según casas de apuestas.
   - Datos actualizados diariamente desde una API externa.

## ¿Cómo funciona el sistema?

El sistema funciona en varios pasos:

### Paso 1: Extracción de Datos (Scraping)
El sistema visita las páginas de ESPN y extrae la información. Cada tipo de dato tiene su propio "scraper" (extractor):
- `espn_schedule_scraper.py` - Obtiene los IDs de los partidos
- `espn_scraper.py` - Extrae los resultados detallados de cada partido
- `player_stats_scraper.py` - Extrae estadísticas de jugadores
- `team_scraper.py` - Extrae estadísticas de equipos
- `standings_scraper.py` - Extrae las clasificaciones
- `injuries_scraper.py` - Extrae reportes de lesiones
- `odds_scraper.py` - Obtiene cuotas de apuestas desde una API

### Paso 2: Almacenamiento Temporal
Los datos extraídos se guardan primero en archivos CSV y JSON en la carpeta `data/raw/`. Esto permite revisar los datos antes de procesarlos.

### Paso 3: Procesamiento y Consolidación (ETL)
El sistema toma todos los archivos individuales y los combina en un solo archivo maestro (`nba_full_dataset.csv`) que contiene toda la información relacionada. Este proceso se llama ETL (Extract, Transform, Load).

### Paso 4: Carga a Base de Datos
Finalmente, el sistema carga todos los datos a una base de datos PostgreSQL usando un sistema inteligente que:
- Detecta automáticamente qué tipo de datos son (números, texto, fechas, etc.)
- Crea las tablas necesarias automáticamente
- Evita duplicados
- Relaciona los datos entre sí (por ejemplo, qué jugadores pertenecen a qué equipos)

## Estructura del Proyecto

```
nba/
├── espn/                    # Extractores de datos de ESPN
│   ├── espn_schedule_scraper.py    # Obtiene IDs de partidos
│   ├── espn_scraper.py             # Extrae resultados de partidos
│   ├── player_stats_scraper.py     # Extrae estadísticas de jugadores
│   ├── team_scraper.py             # Extrae estadísticas de equipos
│   ├── standings_scraper.py        # Extrae clasificaciones
│   ├── injuries_scraper.py         # Extrae reportes de lesiones
│   └── odds_scraper.py             # Obtiene cuotas de apuestas
│
├── etl/                     # Procesamiento y consolidación de datos
│   └── transform_consolidate.py   # Combina todos los datos en uno solo
│
├── utils/                   # Herramientas compartidas
│   ├── db.py               # Conexión a base de datos
│   ├── logger.py           # Sistema de registro de actividades
│   └── common.py           # Funciones útiles compartidas
│
├── data/                    # Datos extraídos
│   ├── raw/                 # Datos sin procesar (CSV, JSON)
│   └── processed/           # Datos procesados y consolidados
│
├── logs/                    # Registros de actividades del sistema
│
├── main.py                  # Programa principal que ejecuta todo
├── load_data.py             # Carga los datos a la base de datos
├── config.yaml              # Configuración del sistema
└── requirements.txt         # Librerías necesarias
```

## Instalación y Configuración

### Requisitos Previos

- Python 3.11 o superior
- PostgreSQL 15 o superior
- Chrome o Chromium (para extraer estadísticas de jugadores)

### Pasos de Instalación

1. **Instalar las dependencias de Python:**
   ```bash
   cd Scrapping/nba
   pip install -r requirements.txt
   ```

2. **Configurar la base de datos:**
   - Asegúrate de que PostgreSQL esté corriendo
   - Edita el archivo `config.yaml` con tus credenciales de base de datos:
     ```yaml
     DATABASE_URL: postgresql://usuario:contraseña@localhost:5432/nba_data
     DB_SCHEMA: espn
     ```

3. **Verificar que todo funciona:**
   ```bash
   python main.py
   ```

## Cómo Usar el Sistema

### Ejecutar el Sistema Completo

El sistema puede ejecutarse de dos formas:

**Opción 1: Ejecución Manual**
```bash
python main.py
```

**Opción 2: Ejecución Automática Programada**
El sistema está configurado para ejecutarse automáticamente todos los días a las 3:00 AM. Solo necesitas dejar el programa corriendo:
```bash
python main.py
```
El sistema se ejecutará automáticamente cada día a la hora programada.

### Extraer Estadísticas de Jugadores Específicas

Si solo quieres extraer estadísticas de jugadores para una temporada específica:

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

### Actualizar Injuries y Odds

Para actualizar los reportes de lesiones y cuotas de apuestas (datos que cambian diariamente):

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

Este script es útil para mantener actualizados los datos de lesiones y cuotas de apuestas sin necesidad de ejecutar todo el sistema de scraping.

**Nota:** Por defecto, el script solo actualiza los archivos CSV/JSON. Si quieres que también actualice la base de datos, usa la opción `--load-db`.

### Cargar Datos a la Base de Datos

Una vez que tengas los datos extraídos, puedes cargarlos a la base de datos:

```bash
python load_data.py
```

Este script:
1. Analiza todos los archivos de datos
2. Detecta automáticamente la estructura de los datos
3. Crea las tablas necesarias en la base de datos
4. Carga todos los datos
5. Muestra un resumen de lo que se cargó

## ¿Dónde se Guardan los Datos?

### Archivos Locales

- **Datos sin procesar:** `data/raw/`
  - `boxscores/` - Resultados de partidos (JSON)
  - `player_stats/` - Estadísticas de jugadores (CSV)
  - `team_stats/` - Estadísticas de equipos (CSV)
  - `standings/` - Clasificaciones (CSV)
  - `injuries/` - Reportes de lesiones (CSV)
  - `odds/` - Cuotas de apuestas (JSON)

- **Datos procesados:** `data/processed/`
  - `nba_full_dataset.csv` - Archivo maestro con todos los datos combinados

### Base de Datos

Los datos también se cargan en PostgreSQL en el esquema `espn` con las siguientes tablas:
- `games` - Partidos y resultados
- `player_stats` - Estadísticas de jugadores
- `team_stats` - Estadísticas de equipos
- `standings` - Clasificaciones
- `injuries` - Lesiones
- `odds` - Cuotas de apuestas

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
- Asegúrate de que la base de datos `nba_data` exista

### No se pueden extraer estadísticas de jugadores
- Asegúrate de tener Chrome o Chromium instalado
- El sistema usa Selenium que requiere ChromeDriver (se instala automáticamente)

### Los datos no se cargan correctamente
- Revisa los logs en `logs/` para ver qué error específico ocurrió
- Verifica que los archivos de datos existan en `data/raw/`
- Asegúrate de que la base de datos tenga espacio suficiente

## Próximos Pasos

Este sistema es parte de un proyecto más grande que incluye:
- Un backend que usa estos datos para hacer predicciones
- Un frontend que muestra las predicciones y permite hacer apuestas virtuales
- Modelos de machine learning que aprenden de estos datos históricos

Los datos extraídos por este sistema alimentan todo el resto del proyecto.
