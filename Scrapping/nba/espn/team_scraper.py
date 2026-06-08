"""
ESPN Team Stats Scraper
=======================

Scraper de estadísticas de equipos NBA por temporada.
Extrae estadísticas ofensivas y defensivas de todos los equipos.

URLs:
- Offensive Leaders: https://www.espn.com/nba/stats/team/_/season/{year}/seasontype/{type}
- Defensive Leaders: https://www.espn.com/nba/stats/team/_/view/opponent/season/{year}/seasontype/{type}
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from pathlib import Path
from loguru import logger
from datetime import datetime

# Selenium para manejo de JavaScript (contenido dinámico)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Mapeo de temporadas a años de ESPN
SEASON_MAPPING = {
    "2023-24": {"year": 2024, "regular": 2, "playoffs": 3},
    "2024-25": {"year": 2025, "regular": 2, "playoffs": 3},
    "2025-26": {"year": 2026, "regular": 2, "playoffs": 3}
}

# Headers para requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}

# Mapeo de abreviaciones de equipos a nombres completos
TEAM_NAMES_MAP = {
    'atl': 'Atlanta Hawks',
    'bos': 'Boston Celtics',
    'bkn': 'Brooklyn Nets',
    'cha': 'Charlotte Hornets',
    'chi': 'Chicago Bulls',
    'cle': 'Cleveland Cavaliers',
    'dal': 'Dallas Mavericks',
    'den': 'Denver Nuggets',
    'det': 'Detroit Pistons',
    'gs': 'Golden State Warriors',
    'hou': 'Houston Rockets',
    'ind': 'Indiana Pacers',
    'lac': 'LA Clippers',
    'lal': 'Los Angeles Lakers',
    'mem': 'Memphis Grizzlies',
    'mia': 'Miami Heat',
    'mil': 'Milwaukee Bucks',
    'min': 'Minnesota Timberwolves',
    'no': 'New Orleans Pelicans',
    'ny': 'New York Knicks',
    'okc': 'Oklahoma City Thunder',
    'orl': 'Orlando Magic',
    'phi': 'Philadelphia 76ers',
    'phx': 'Phoenix Suns',
    'por': 'Portland Trail Blazers',
    'sac': 'Sacramento Kings',
    'sa': 'San Antonio Spurs',
    'tor': 'Toronto Raptors',
    'utah': 'Utah Jazz',
    'wsh': 'Washington Wizards'
}

# Mapeo inverso: nombre completo a abreviación
TEAM_ABBREV_MAP = {v: k for k, v in TEAM_NAMES_MAP.items()}


def parse_espn_team_table(soup: BeautifulSoup) -> list:
    """
    Parsear tabla dual de ESPN para estadísticas de equipos
    
    ESPN usa dos tablas separadas:
    - .Table--fixed-left: RANK, NAME
    - .Table__Scroller: Estadísticas numéricas
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Lista de diccionarios con datos de equipos
    """
    
    teams_data = []
    
    try:
        # Buscar contenedor principal de la tabla responsiva
        responsive_table = soup.find('div', class_='ResponsiveTable')
        
        if not responsive_table:
            logger.warning("   [WARN] No se encontro contenedor .ResponsiveTable")
            return []
        
        # Buscar tabla fija (nombres de equipos)
        fixed_table_elem = responsive_table.find('table', class_='Table--fixed-left')
        
        # Buscar tabla scrollable (estadísticas)
        # Intentar diferentes clases posibles
        scrollable_container = responsive_table.find('div', class_='Table__Scroller')
        if not scrollable_container:
            scrollable_container = responsive_table.find('div', class_='Table_Scroller')
        if not scrollable_container:
            scrollable_container = responsive_table.find('div', class_='Table_ScrollerWrapper')
        
        if not fixed_table_elem:
            logger.warning("   [WARN] No se encontro tabla fija (table.Table--fixed-left)")
            return []
        
        if not scrollable_container:
            logger.warning("   [WARN] No se encontro contenedor scrollable")
            return []
        
        # Buscar tabla dentro del contenedor scrollable
        scrollable_table_elem = scrollable_container.find('table')
        if not scrollable_table_elem and scrollable_container.find('div', class_='Table_Scroller'):
            scrollable_table_elem = scrollable_container.find('div', class_='Table_Scroller').find('table')
        
        if not scrollable_table_elem:
            logger.warning("   [WARN] No se encontro tabla dentro de .Table__Scroller")
            return []
        
        # Extraer encabezados de tabla fija
        fixed_headers = []
        fixed_thead = fixed_table_elem.find('thead')
        if fixed_thead:
            fixed_header_row = fixed_thead.find('tr')
            if fixed_header_row:
                fixed_headers = [th.get_text(strip=True) for th in fixed_header_row.find_all('th')]
        
        # Extraer encabezados de tabla scrollable
        scrollable_headers = []
        scrollable_thead = scrollable_table_elem.find('thead')
        if scrollable_thead:
            scrollable_header_row = scrollable_thead.find('tr')
            if scrollable_header_row:
                scrollable_headers = [th.get_text(strip=True) for th in scrollable_header_row.find_all('th')]
        
        # Combinar encabezados (excluir "TEAM" de fixed_headers ya que lo procesamos por separado)
        # fixed_headers tiene: [RK, TEAM] - solo necesitamos RK
        fixed_headers_filtered = fixed_headers[:1] if len(fixed_headers) > 0 else []  # Solo RK
        all_headers = fixed_headers_filtered + scrollable_headers
        
        # Extraer filas de ambas tablas
        fixed_tbody = fixed_table_elem.find('tbody')
        scrollable_tbody = scrollable_table_elem.find('tbody')
        
        if not fixed_tbody or not scrollable_tbody:
            logger.warning("   [WARN] No se encontro tbody en las tablas")
            return []
        
        fixed_rows = fixed_tbody.find_all('tr')
        scrollable_rows = scrollable_tbody.find_all('tr')
        
        # Combinar datos de ambas tablas
        max_rows = min(len(fixed_rows), len(scrollable_rows))
        
        for i in range(max_rows):
            # Extraer celdas de tabla fija
            fixed_cells = fixed_rows[i].find_all('td')
            fixed_values = []
            team_name = None
            team_abbrev = None
            
            # El nombre del equipo está en la segunda celda (índice 1) de la tabla fija
            # Hay un <a class="AnchorLink"> con href="/nba/team//name/ind/indiana-pacers"
            if len(fixed_cells) > 1:
                team_cell = fixed_cells[1]  # Segunda celda (índice 1)
                
                # Buscar el link del equipo - buscar en toda la celda (puede estar anidado en divs)
                # El link tiene clase "AnchorLink" y href="/nba/team//name/ind/indiana-pacers"
                team_link = team_cell.find('a', class_='AnchorLink')
                if not team_link:
                    # Buscar cualquier link dentro de la celda o en sus descendientes
                    team_link = team_cell.find('a')
                
                if team_link:
                    # El texto visible es la abreviación (ej: "IND")
                    team_abbrev = team_link.get_text(strip=True)
                    # El nombre completo está en el href (ej: "/nba/team//name/ind/indiana-pacers")
                    team_url = team_link.get('href', '')
                    
                    # Extraer nombre completo de la URL
                    # La URL puede ser: /nba/team//name/ind/indiana-pacers
                    if '/name/' in team_url:
                        parts = team_url.split('/name/')
                        if len(parts) > 1:
                            # parts[1] = "ind/indiana-pacers"
                            url_parts = parts[1].split('/')
                            if len(url_parts) >= 2:
                                # url_parts[0] = "ind" (abreviación)
                                # url_parts[1] = "indiana-pacers" (nombre completo)
                                team_abbrev_from_url = url_parts[0]
                                team_name_slug = url_parts[1]
                                # Convertir slug a nombre completo (ej: "indiana-pacers" -> "Indiana Pacers")
                                team_name = team_name_slug.replace('-', ' ').title()
                                # Si no tenemos abreviación del texto, usar la de la URL
                                if not team_abbrev:
                                    team_abbrev = team_abbrev_from_url
                    else:
                        # Si no podemos extraer de la URL, usar el texto del link como abreviación
                        if not team_abbrev:
                            team_abbrev = team_link.get_text(strip=True)
                        # Intentar obtener nombre completo del mapa
                        team_name = TEAM_NAMES_MAP.get(team_abbrev.lower())
                else:
                    # Fallback: buscar texto directamente en la celda
                    team_name = team_cell.get_text(strip=True)
            
            # Extraer valores de tabla fija (excluir la celda del equipo que ya procesamos)
            # La tabla fija tiene: [RK, TEAM] - solo necesitamos RK (índice 0)
            if len(fixed_cells) > 0:
                # Solo agregar RK (primera celda), excluir TEAM (segunda celda)
                fixed_values.append(fixed_cells[0].get_text(strip=True))
            
            # Extraer celdas de tabla scrollable
            scrollable_cells = scrollable_rows[i].find_all('td')
            scrollable_values = []
            for cell in scrollable_cells:
                scrollable_values.append(cell.get_text(strip=True))
            
            # Si no tenemos abreviación, buscarla en el mapa usando el nombre completo
            if not team_abbrev and team_name:
                team_abbrev = TEAM_ABBREV_MAP.get(team_name)
                # Si aún no tenemos, intentar buscar por coincidencia parcial
                if not team_abbrev:
                    for full_name, abbrev in TEAM_ABBREV_MAP.items():
                        if team_name.lower() in full_name.lower() or full_name.lower() in team_name.lower():
                            team_abbrev = abbrev
                            break
            
            # Combinar ambas filas (fixed_values solo tiene RK, scrollable_values tiene el resto)
            combined_values = fixed_values + scrollable_values
            
            # Crear diccionario con los datos
            row_data = {
                'rank': i + 1,
                'team_name': team_name,
                'team_abbrev': team_abbrev,
            }
            
            # Agregar el resto de columnas
            for idx, header in enumerate(all_headers):
                if idx < len(combined_values):
                    col_name = header.strip().lower().replace(' ', '_').replace('%', '_pct').replace('-', '_')
                    # Prefijo para evitar conflictos
                    if col_name not in ['rank', 'name']:
                        row_data[col_name] = combined_values[idx]
            
            teams_data.append(row_data)
        
        logger.info(f"   [DATA] {len(teams_data)} equipos parseados")
        return teams_data
        
    except Exception as e:
        logger.error(f"   [ERROR] Error parseando tabla: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def scrape_team_stats_offensive(season: str, season_type: str) -> pd.DataFrame:
    """
    Scrapear estadísticas ofensivas de todos los equipos usando Selenium
    
    Args:
        season: Temporada ("2023-24", "2024-25")
        season_type: Tipo ("regular", "playoffs")
        
    Returns:
        DataFrame con estadísticas ofensivas
    """
    
    if season not in SEASON_MAPPING:
        logger.error(f"[ERROR] Temporada invalida: {season}")
        return None
    
    year = SEASON_MAPPING[season]["year"]
    season_type_code = SEASON_MAPPING[season][season_type]
    
    url = f"https://www.espn.com/nba/stats/team/_/season/{year}/seasontype/{season_type_code}"
    
    logger.info(f"[WEB] Scrapeando estadisticas ofensivas")
    logger.info(f"   URL: {url}")
    
    # Configurar Chrome en modo headless
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = None
    
    try:
        # Iniciar Chrome con webdriver-manager
        logger.info("[BROWSER] Iniciando navegador...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navegar a la URL
        logger.info("[BROWSER] Navegando a la pagina...")
        driver.get(url)
        
        # Esperar a que la tabla cargue
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ResponsiveTable")))
        logger.info("[BROWSER] Tabla encontrada")
        
        # Esperar un poco más para que el contenido dinámico cargue
        time.sleep(2)
        
        # Obtener HTML final
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'lxml')
        
        teams_data = parse_espn_team_table(soup)
        
        if not teams_data:
            logger.warning("   [WARN] No se pudieron extraer datos ofensivos")
            return None
        
        df = pd.DataFrame(teams_data)
        
        # Agregar prefijo 'off_' a las columnas estadísticas (excepto rank, team_name, team_abbrev)
        stat_columns = [col for col in df.columns if col not in ['rank', 'team_name', 'team_abbrev']]
        rename_dict = {col: f'off_{col}' for col in stat_columns}
        df = df.rename(columns=rename_dict)
        
        logger.info(f"   [OK] {len(df)} equipos extraidos (ofensivos)")
        return df
        
    except Exception as e:
        logger.error(f"   [ERROR] Error inesperado: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
        
    finally:
        # Cerrar navegador
        if driver:
            driver.quit()
            logger.info("[BROWSER] Navegador cerrado")


def scrape_team_stats_defensive(season: str, season_type: str) -> pd.DataFrame:
    """
    Scrapear estadísticas defensivas de todos los equipos usando Selenium
    
    Args:
        season: Temporada ("2023-24", "2024-25")
        season_type: Tipo ("regular", "playoffs")
        
    Returns:
        DataFrame con estadísticas defensivas
    """
    
    if season not in SEASON_MAPPING:
        logger.error(f"[ERROR] Temporada invalida: {season}")
        return None
    
    year = SEASON_MAPPING[season]["year"]
    season_type_code = SEASON_MAPPING[season][season_type]
    
    url = f"https://www.espn.com/nba/stats/team/_/view/opponent/season/{year}/seasontype/{season_type_code}"
    
    logger.info(f"[WEB] Scrapeando estadisticas defensivas")
    logger.info(f"   URL: {url}")
    
    # Configurar Chrome en modo headless
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = None
    
    try:
        # Iniciar Chrome con webdriver-manager
        logger.info("[BROWSER] Iniciando navegador...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navegar a la URL
        logger.info("[BROWSER] Navegando a la pagina...")
        driver.get(url)
        
        # Esperar a que la tabla cargue
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ResponsiveTable")))
        logger.info("[BROWSER] Tabla encontrada")
        
        # Esperar un poco más para que el contenido dinámico cargue
        time.sleep(2)
        
        # Obtener HTML final
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'lxml')
        
        teams_data = parse_espn_team_table(soup)
        
        if not teams_data:
            logger.warning("   [WARN] No se pudieron extraer datos defensivos")
            return None
        
        df = pd.DataFrame(teams_data)
        
        # Agregar prefijo 'def_' a las columnas estadísticas (excepto rank, team_name, team_abbrev)
        stat_columns = [col for col in df.columns if col not in ['rank', 'team_name', 'team_abbrev']]
        rename_dict = {col: f'def_{col}' for col in stat_columns}
        df = df.rename(columns=rename_dict)
        
        logger.info(f"   [OK] {len(df)} equipos extraidos (defensivos)")
        return df
        
    except Exception as e:
        logger.error(f"   [ERROR] Error inesperado: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
        
    finally:
        # Cerrar navegador
        if driver:
            driver.quit()
            logger.info("[BROWSER] Navegador cerrado")


def scrape_all_teams_stats(season: str, season_type: str):
    """
    Scrapear estadísticas ofensivas y defensivas de todos los equipos
    
    Args:
        season: Temporada ("2023-24", "2024-25")
        season_type: Tipo ("regular", "playoffs")
    """
    
    logger.info("="*80)
    logger.info(f"SCRAPING DE ESTADISTICAS DE EQUIPOS")
    logger.info(f"   Temporada: {season}")
    logger.info(f"   Tipo: {season_type.upper()}")
    logger.info("="*80 + "\n")
    
    # Scrapear estadísticas ofensivas
    df_offensive = scrape_team_stats_offensive(season, season_type)
    
    # Scrapear estadísticas defensivas
    df_defensive = scrape_team_stats_defensive(season, season_type)
    
    if df_offensive is None or df_defensive is None:
        logger.error("[ERROR] No se pudieron obtener todas las estadisticas")
        return
    
    # Asegurar que team_abbrev esté presente en ambos DataFrames
    # Si no tenemos team_abbrev, intentar obtenerlo del team_name
    for df in [df_offensive, df_defensive]:
        if 'team_abbrev' in df.columns:
            # Rellenar team_abbrev faltantes usando team_name
            mask = df['team_abbrev'].isna() | (df['team_abbrev'] == '')
            if mask.any():
                df.loc[mask, 'team_abbrev'] = df.loc[mask, 'team_name'].map(TEAM_ABBREV_MAP)
    
    # Agregar season y season_type a cada DataFrame
    df_offensive['season'] = season
    df_offensive['season_type'] = season_type
    df_defensive['season'] = season
    df_defensive['season_type'] = season_type
    
    # Guardar datos por categoría (offensive y defensive por separado)
    save_team_stats_by_category(df_offensive, df_defensive, season, season_type)
    
    logger.info("="*80)
    logger.info("RESUMEN DE SCRAPING")
    logger.info("="*80)
    logger.info(f"\n[RESULT] Equipos extraidos (ofensivos): {len(df_offensive)}")
    logger.info(f"[RESULT] Equipos extraidos (defensivos): {len(df_defensive)}")
    logger.info(f"[SAVE] Datos guardados en: data/raw/team_stats/{season}_{season_type}/")
    logger.info(f"   - offensive/all_teams.csv")
    logger.info(f"   - defensive/all_teams.csv\n")


def save_team_stats_by_category(df_offensive: pd.DataFrame, df_defensive: pd.DataFrame, season: str, season_type: str):
    """
    Guardar estadísticas de equipos por categoría (offensive y defensive)
    
    Args:
        df_offensive: DataFrame con estadísticas ofensivas
        df_defensive: DataFrame con estadísticas defensivas
        season: Temporada
        season_type: Tipo de temporada
    """
    
    # Crear directorio base
    season_dir = Path(f"data/raw/team_stats/{season}_{season_type}")
    season_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\n[SAVE] Guardando datos en {season_dir}/")
    
    # Guardar estadísticas ofensivas
    offensive_dir = season_dir / "offensive"
    offensive_dir.mkdir(parents=True, exist_ok=True)
    
    if df_offensive is not None and not df_offensive.empty:
        file_path = offensive_dir / "all_teams.csv"
        df_offensive.to_csv(file_path, index=False)
        logger.info(f"   [OK] offensive/all_teams.csv - {len(df_offensive)} equipos")
    else:
        logger.warning("   [WARN] Sin datos ofensivos para guardar")
    
    # Guardar estadísticas defensivas
    defensive_dir = season_dir / "defensive"
    defensive_dir.mkdir(parents=True, exist_ok=True)
    
    if df_defensive is not None and not df_defensive.empty:
        file_path = defensive_dir / "all_teams.csv"
        df_defensive.to_csv(file_path, index=False)
        logger.info(f"   [OK] defensive/all_teams.csv - {len(df_defensive)} equipos")
    else:
        logger.warning("   [WARN] Sin datos defensivos para guardar")
    
    logger.info("[OK] Datos guardados exitosamente\n")
