#!/usr/bin/env python3
"""
ESPN Player Stats Scraper
=========================

Scraper de estadísticas de jugadores NBA por temporada.
Extrae Top 50 jugadores en cada categoría estadística.

Uso:
    python -m espn.player_stats_scraper --season "2023-24" --type "regular"
    python -m espn.player_stats_scraper --season "2023-24" --type "playoffs"
    python -m espn.player_stats_scraper --season "2024-25" --type "regular"
    python -m espn.player_stats_scraper --season "2024-25" --type "playoffs"
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import argparse
from pathlib import Path
from datetime import datetime
from loguru import logger
import sys

# Selenium para manejo de JavaScript (Show More button)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configurar logger (sin emojis para evitar problemas de encoding)
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
logger.add("logs/player_stats_scraper_{time}.log", rotation="1 day", retention="7 days", encoding="utf-8")

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Mapeo de temporadas a años de ESPN
SEASON_MAPPING = {
    "2023-24": {"year": 2024, "regular": 2, "playoffs": 3},
    "2024-25": {"year": 2025, "regular": 2, "playoffs": 3},
    "2025-26": {"year": 2026, "regular": 2, "playoffs": 3}
}

# Categorías de estadísticas
STAT_CATEGORIES = {
    "points": {
        "name": "Points",
        "url_stat": "scoring",
        "main_column": "PTS",
        "description": "Puntos por partido"
    },
    "assists": {
        "name": "Assists", 
        "url_stat": "assists",
        "main_column": "AST",
        "description": "Asistencias por partido"
    },
    "three_pointers": {
        "name": "3-Pointers Made",
        "url_stat": "threePointFieldGoalsMade",
        "main_column": "3PM",
        "description": "Triples anotados por partido"
    },
    "rebounds": {
        "name": "Rebounds",
        "url_stat": "rebounds",
        "main_column": "REB",
        "description": "Rebotes por partido"
    },
    "blocks": {
        "name": "Blocks",
        "url_stat": "blocks",
        "main_column": "BLK",
        "description": "Bloqueos por partido"
    },
    "steals": {
        "name": "Steals",
        "url_stat": "steals",
        "main_column": "STL",
        "description": "Robos por partido"
    }
}

# Headers HTTP
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

# ============================================================================
# FUNCIONES DE SCRAPING
# ============================================================================

def scrape_category_leaders(category: str, season: str, season_type: str, limit: int = 50) -> pd.DataFrame:
    """
    Scrapear líderes de una categoría específica
    
    Args:
        category: Categoría (points, assists, rebounds, etc.)
        season: Temporada ("2023-24", "2024-25")
        season_type: Tipo ("regular", "playoffs")
        limit: Cantidad de jugadores a extraer (default: 50)
        
    Returns:
        DataFrame con estadísticas de jugadores
    """
    
    if season not in SEASON_MAPPING:
        logger.error(f"[ERROR] Temporada invalida: {season}")
        return None
    
    # Construir URL simple (sin tabla específica)
    year = SEASON_MAPPING[season]["year"]
    season_type_code = SEASON_MAPPING[season][season_type]
    
    url = f"https://www.espn.com/nba/stats/player/_/season/{year}/seasontype/{season_type_code}"
    
    logger.info(f"[WEB] Scrapeando: {STAT_CATEGORIES[category]['name']} - {season} {season_type}")
    logger.info(f"   URL: {url}")
    
    try:
        # Hacer request
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Parsear HTML
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Extraer tabla de estadísticas usando estructura de ESPN (tabla fija + scrollable)
        players_data = parse_espn_dual_table(soup, category, season, season_type, limit)
        
        if players_data:
            df = pd.DataFrame(players_data)
            logger.info(f"   [OK] {len(df)} jugadores extraidos")
            return df
        else:
            logger.warning(f"   [WARN] No se pudieron extraer datos")
            return None
            
    except requests.RequestException as e:
        logger.error(f"   [ERROR] Error de conexion: {e}")
        return None
    except Exception as e:
        logger.error(f"   [ERROR] Error inesperado: {e}")
        return None

def parse_all_player_stats(soup: BeautifulSoup, season: str, season_type: str, limit: int) -> list:
    """
    Parsear TODAS las estadísticas de jugadores de la tabla de ESPN
    
    ESPN muestra todas las estadísticas en una sola tabla con estructura dual:
    - .Table--fixed-left: RANK, NAME, POSITION  
    - .Table__Scroller: GP, MIN, PTS, FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, REB, AST, STL, BLK, TO, PF
    
    Args:
        soup: BeautifulSoup object
        season: Temporada
        season_type: Tipo de temporada
        limit: Límite de jugadores (default: 50)
        
    Returns:
        Lista de diccionarios con TODAS las estadísticas de cada jugador
    """
    
    players_data = []
    
    try:
        # Buscar contenedor principal de la tabla responsiva
        responsive_table = soup.find('div', class_='ResponsiveTable')
        
        if not responsive_table:
            logger.warning("   [WARN] No se encontro contenedor .ResponsiveTable")
            return []
        
        # Buscar tabla fija (nombres de jugadores)
        fixed_table_elem = responsive_table.find('table', class_='Table--fixed-left')
        
        # Buscar tabla scrollable (estadísticas)
        scrollable_container = responsive_table.find('div', class_='Table__Scroller')
        
        if not fixed_table_elem:
            logger.warning("   [WARN] No se encontro tabla fija (table.Table--fixed-left)")
            return []
        
        if not scrollable_container:
            logger.warning("   [WARN] No se encontro contenedor scrollable (.Table__Scroller)")
            return []
        
        scrollable_table_elem = scrollable_container.find('table')
        
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
        
        # Combinar todos los encabezados
        all_headers = fixed_headers + scrollable_headers
        logger.info(f"   [DATA] Columnas detectadas: {len(all_headers)}")
        
        # Extraer filas de ambas tablas
        fixed_tbody = fixed_table_elem.find('tbody')
        scrollable_tbody = scrollable_table_elem.find('tbody')
        
        if not fixed_tbody or not scrollable_tbody:
            logger.warning("   [WARN] No se encontro tbody en las tablas")
            return []
        
        fixed_rows = fixed_tbody.find_all('tr')
        scrollable_rows = scrollable_tbody.find_all('tr')
        
        # Combinar datos de ambas tablas
        max_rows = min(len(fixed_rows), len(scrollable_rows), limit)
        
        for i in range(max_rows):
            # Extraer celdas de tabla fija
            fixed_cells = fixed_rows[i].find_all('td')
            fixed_values = []
            player_id = None
            player_name = None
            
            for idx, cell in enumerate(fixed_cells):
                if idx == 1:  # Columna de nombre
                    # Buscar link del jugador
                    player_link = cell.find('a')
                    if player_link:
                        player_name = player_link.get_text(strip=True)
                        player_url = player_link.get('href', '')
                        player_id = extract_player_id(player_url)
                    else:
                        # Fallback: buscar en div
                        name_elem = cell.find('div', class_='athleteCell__name') or cell.find('div') or cell
                        player_name = name_elem.get_text(strip=True)
                    
                    fixed_values.append(player_name)
                else:
                    fixed_values.append(cell.get_text(strip=True))
            
            # Extraer celdas de tabla scrollable (TODAS las estadísticas)
            scrollable_cells = scrollable_rows[i].find_all('td')
            scrollable_values = [cell.get_text(strip=True) for cell in scrollable_cells]
            
            # Combinar ambas filas
            combined_values = fixed_values + scrollable_values
            
            # Crear diccionario con TODAS las estadísticas
            row_data = {
                'rank': i + 1,
                'player_id': player_id,
                'player_name': player_name,
                'season': season,
                'season_type': season_type,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Agregar TODAS las columnas de estadísticas
            for idx, header in enumerate(all_headers):
                if idx < len(combined_values):
                    col_name = header.strip().lower().replace(' ', '_').replace('%', '_percent').replace('-', '_')
                    row_data[col_name] = combined_values[idx]
            
            players_data.append(row_data)
        
        logger.info(f"   [DATA] {len(players_data)} jugadores parseados con {len(all_headers)} estadisticas")
        return players_data
        
    except requests.RequestException as e:
        logger.error(f"[ERROR] Error de conexion: {e}")
        return []
    except Exception as e:
        logger.error(f"[ERROR] Error inesperado: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def parse_espn_dual_table(soup: BeautifulSoup, category: str, season: str, season_type: str, limit: int) -> list:
    """
    Parsear tabla dual de ESPN (tabla fija + tabla scrollable)
    
    ESPN usa dos tablas separadas:
    - .Table--fixed-left: RANK, NAME, POSITION
    - .Table__Scroller: Estadísticas numéricas
    
    Args:
        soup: BeautifulSoup object
        category: Categoría de estadística
        season: Temporada
        season_type: Tipo de temporada
        limit: Límite de jugadores
        
    Returns:
        Lista de diccionarios con datos de jugadores
    """
    
    players_data = []
    
    try:
        # Buscar contenedor principal de la tabla responsiva
        responsive_table = soup.find('div', class_='ResponsiveTable')
        
        if not responsive_table:
            logger.warning("   [WARN] No se encontro contenedor .ResponsiveTable")
            return []
        
        # Buscar tabla fija (nombres de jugadores) - tiene clase Table--fixed-left
        fixed_table_elem = responsive_table.find('table', class_='Table--fixed-left')
        
        # Buscar tabla scrollable (estadísticas) - está dentro de .Table__Scroller
        scrollable_container = responsive_table.find('div', class_='Table__Scroller')
        
        if not fixed_table_elem:
            logger.warning("   [WARN] No se encontro tabla fija (table.Table--fixed-left)")
            return []
        
        if not scrollable_container:
            logger.warning("   [WARN] No se encontro contenedor scrollable (.Table__Scroller)")
            return []
        
        scrollable_table_elem = scrollable_container.find('table')
        
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
        
        # Renombrar encabezados fijos según estructura esperada
        if len(fixed_headers) >= 2:
            fixed_headers[0] = 'RANK'
            fixed_headers[1] = 'NAME'
            if len(fixed_headers) >= 3:
                fixed_headers[2] = 'POSITION'
        
        # Extraer encabezados de tabla scrollable
        scrollable_headers = []
        scrollable_thead = scrollable_table_elem.find('thead')
        if scrollable_thead:
            scrollable_header_row = scrollable_thead.find('tr')
            if scrollable_header_row:
                scrollable_headers = [th.get_text(strip=True) for th in scrollable_header_row.find_all('th')]
        
        # Combinar encabezados
        all_headers = fixed_headers + scrollable_headers
        
        # Extraer filas de ambas tablas
        fixed_tbody = fixed_table_elem.find('tbody')
        scrollable_tbody = scrollable_table_elem.find('tbody')
        
        if not fixed_tbody or not scrollable_tbody:
            logger.warning("   [WARN] No se encontro tbody en las tablas")
            return []
        
        fixed_rows = fixed_tbody.find_all('tr')
        scrollable_rows = scrollable_tbody.find_all('tr')
        
        # Combinar datos de ambas tablas
        max_rows = min(len(fixed_rows), len(scrollable_rows), limit)
        
        for i in range(max_rows):
            # Extraer celdas de tabla fija
            fixed_cells = fixed_rows[i].find_all('td')
            fixed_values = []
            
            for idx, cell in enumerate(fixed_cells):
                if idx == 1:  # Columna de nombre
                    # Buscar link del jugador
                    player_link = cell.find('a')
                    if player_link:
                        player_name = player_link.get_text(strip=True)
                        player_url = player_link.get('href', '')
                        player_id = extract_player_id(player_url)
                    else:
                        # Fallback: buscar en div o span
                        name_elem = cell.find('div', class_='athleteCell__name') or cell.find('div') or cell
                        player_name = name_elem.get_text(strip=True)
                        player_id = None
                    
                    fixed_values.append(player_name)
                else:
                    fixed_values.append(cell.get_text(strip=True))
            
            # Extraer celdas de tabla scrollable
            scrollable_cells = scrollable_rows[i].find_all('td')
            scrollable_values = [cell.get_text(strip=True) for cell in scrollable_cells]
            
            # Combinar ambas filas
            combined_values = fixed_values + scrollable_values
            
            # Crear diccionario con los datos
            row_data = {
                'rank': i + 1,
                'player_id': player_id if 'player_id' in locals() else None,
                'player_name': player_name if 'player_name' in locals() else combined_values[1] if len(combined_values) > 1 else None,
                'season': season,
                'season_type': season_type,
                'stat_category': category,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Agregar el resto de columnas
            for idx, header in enumerate(all_headers):
                if idx < len(combined_values):
                    col_name = header.strip().lower().replace(' ', '_').replace('%', '_pct')
                    row_data[col_name] = combined_values[idx]
            
            players_data.append(row_data)
        
        logger.info(f"   [DATA] {len(players_data)} jugadores parseados")
        return players_data
        
    except Exception as e:
        logger.error(f"   [ERROR] Error parseando tabla: {e}")
        return []


def extract_player_id(url: str) -> str:
    """
    Extraer player_id de una URL de ESPN
    
    Args:
        url: URL del jugador (ej: /nba/player/_/id/3945274/luka-doncic)
        
    Returns:
        player_id o None
    """
    try:
        if '/id/' in url:
            parts = url.split('/id/')
            if len(parts) > 1:
                player_id = parts[1].split('/')[0]
                return player_id
    except:
        pass
    
    return None

# ============================================================================
# FUNCIONES DE GUARDADO
# ============================================================================

def save_season_data_unified(df: pd.DataFrame, season: str, season_type: str):
    """
    Guardar datos unificados de una temporada en un solo archivo
    
    Args:
        df: DataFrame con todas las estadísticas
        season: Temporada
        season_type: Tipo de temporada
    """
    
    # Crear directorio
    season_dir = Path(f"data/raw/player_stats/{season}_{season_type}")
    season_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\n[SAVE] Guardando datos en {season_dir}/")
    
    if df is not None and not df.empty:
        file_path = season_dir / "all_stats.csv"
        df.to_csv(file_path, index=False)
        logger.info(f"   [OK] all_stats.csv - {len(df)} jugadores, {len(df.columns)} columnas")
    else:
        logger.warning(f"   [WARN] Sin datos para guardar")
    
    logger.info("[OK] Datos guardados exitosamente\n")

def save_season_data(results: dict, season: str, season_type: str):
    """
    Guardar datos de una temporada completa (DEPRECADA - usar save_season_data_unified)
    
    Args:
        results: Diccionario con DataFrames por categoría
        season: Temporada
        season_type: Tipo de temporada
    """
    
    # Crear directorio
    season_dir = Path(f"data/raw/player_stats/{season}_{season_type}")
    season_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\n[SAVE] Guardando datos en {season_dir}/")
    
    for category, df in results.items():
        if df is not None and not df.empty:
            file_path = season_dir / f"{category}.csv"
            df.to_csv(file_path, index=False)
            logger.info(f"   [OK] {category}.csv - {len(df)} registros")
        else:
            logger.warning(f"   [WARN] {category} - Sin datos")
    
    logger.info("[OK] Datos guardados exitosamente\n")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def scrape_player_season_stats(season: str, season_type: str):
    """
    Scrapear estadísticas completas de jugadores para una temporada
    
    Usa Selenium para hacer clic en "Show More" y cargar todos los jugadores
    
    Args:
        season: Temporada ("2023-24", "2024-25")
        season_type: Tipo ("regular", "playoffs")
    """
    
    logger.info("="*80)
    logger.info(f"SCRAPING DE ESTADISTICAS DE JUGADORES")
    logger.info(f"   Temporada: {season}")
    logger.info(f"   Tipo: {season_type.upper()}")
    logger.info("="*80 + "\n")
    
    if season not in SEASON_MAPPING:
        logger.error(f"[ERROR] Temporada invalida: {season}")
        return None
    
    year = SEASON_MAPPING[season]["year"]
    season_type_code = SEASON_MAPPING[season][season_type]
    url = f"https://www.espn.com/nba/stats/player/_/season/{year}/seasontype/{season_type_code}"
    
    logger.info(f"[WEB] Scrapeando estadisticas de jugadores")
    logger.info(f"   URL: {url}")
    
    # Configurar Chromium en modo headless
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Nueva sintaxis headless
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = None
    
    try:
        # Iniciar Chrome/Chromium con webdriver-manager
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
        
        # Hacer scroll y clic en "Show More" hasta cargar todos los datos
        show_more_clicks = 0
        max_clicks = 10  # Límite de seguridad
        
        while show_more_clicks < max_clicks:
            try:
                # Scroll hacia abajo
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                # Buscar botón "Show More"
                show_more_button = driver.find_element(By.CSS_SELECTOR, ".loadMore__link")
                
                if show_more_button and show_more_button.is_displayed():
                    logger.info(f"[BROWSER] Haciendo clic en 'Show More' ({show_more_clicks + 1})...")
                    
                    # Scroll al botón para asegurarnos que esté visible
                    driver.execute_script("arguments[0].scrollIntoView(true);", show_more_button)
                    time.sleep(0.5)
                    
                    # Hacer clic usando JavaScript (más confiable)
                    driver.execute_script("arguments[0].click();", show_more_button)
                    time.sleep(2)  # Esperar a que carguen nuevos datos
                    show_more_clicks += 1
                else:
                    break
                    
            except (NoSuchElementException, TimeoutException):
                logger.info("[BROWSER] No hay mas boton 'Show More'")
                break
        
        logger.info(f"[BROWSER] Clicks en 'Show More': {show_more_clicks}")
        
        # Esperar a que termine de cargar
        time.sleep(2)
        
        # Obtener HTML final
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'lxml')
        
        # Extraer TODAS las estadísticas
        players_data = parse_all_player_stats(soup, season, season_type, limit=999999)  # Sin límite
        
        if not players_data:
            logger.warning("[WARN] No se pudieron extraer datos")
            return None
        
        # Convertir a DataFrame
        df = pd.DataFrame(players_data)
        logger.info(f"[OK] {len(df)} jugadores extraidos con todas sus estadisticas")
        
        # Guardar datos
        save_season_data_unified(df, season, season_type)
        
        # Resumen final
        logger.info("="*80)
        logger.info("RESUMEN DE SCRAPING")
        logger.info("="*80)
        logger.info(f"\n[RESULT] Jugadores extraidos: {len(df)}")
        logger.info(f"[RESULT] Columnas de datos: {len(df.columns)}")
        logger.info(f"[SAVE] Datos guardados en: data/raw/player_stats/{season}_{season_type}/all_stats.csv\n")
        
        return df
        
    except Exception as e:
        logger.error(f"[ERROR] Error durante scraping: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
        
    finally:
        # Cerrar navegador
        if driver:
            driver.quit()
            logger.info("[BROWSER] Navegador cerrado")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal con argumentos de línea de comandos"""
    
    parser = argparse.ArgumentParser(
        description='Scraper de estadísticas de jugadores NBA'
    )
    
    parser.add_argument(
        '--season',
        type=str,
        required=True,
        choices=['2023-24', '2024-25', '2025-26'],
        help='Temporada a scrapear'
    )
    
    parser.add_argument(
        '--type',
        type=str,
        required=True,
        choices=['regular', 'playoffs'],
        help='Tipo de temporada'
    )
    
    args = parser.parse_args()
    
    # Crear directorio de logs si no existe
    os.makedirs("logs", exist_ok=True)
    
    # Ejecutar scraping
    scrape_player_season_stats(args.season, args.type)

if __name__ == "__main__":
    main()

