import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from loguru import logger

def scrape_team_stats(team_abbrev, team_name):
    """
    Extraer rendimiento promedio por temporada de un equipo.
    
    Args:
        team_abbrev (str): Abreviación del equipo (ej: 'bos')
        team_name (str): Nombre completo del equipo (ej: 'boston-celtics')
        
    Returns:
        dict: Estadísticas del equipo
    """
    url = f"https://www.espn.com/nba/team/stats/_/name/{team_abbrev}/{team_name}"
    
    try:
        headers = {
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
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")
        
        # Buscar tabla principal de promedios
        team_stats = extract_team_averages(soup)
        
        if team_stats:
            logger.info(f"Estadísticas extraídas exitosamente para {team_name}")
            return team_stats
        else:
            logger.warning(f"No se encontraron estadísticas para {team_name}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error de conexión al obtener estadísticas de {team_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al procesar estadísticas de {team_name}: {e}")
        return None

def extract_team_averages(soup):
    """
    Extraer estadísticas promedio desde la tabla principal.
    
    Args:
        soup: BeautifulSoup object del HTML
        
    Returns:
        dict: Estadísticas promedio del equipo
    """
    try:
        # Buscar el contenedor principal con la clase específica
        main_container = soup.find('div', class_='ResponsiveTable ResponsiveTable--fixed-left mt4 Table2__title--remove-capitalization')
        if not main_container:
            logger.warning("No se encontró el contenedor principal de estadísticas")
            # Fallback: buscar todas las tablas
            tables = soup.find_all("table")
            logger.info(f"Encontradas {len(tables)} tablas")
            
            # Buscar la tabla con estadísticas de porcentajes (FG%, 3P%, etc.)
            target_table = None
            for table in tables:
                table_text = table.get_text()
                if "FG%" in table_text and "3P%" in table_text:
                    target_table = table
                    logger.info("✅ Tabla con estadísticas de porcentajes encontrada")
                    break
            
            if not target_table:
                logger.warning("No se encontró tabla con estadísticas de porcentajes")
                return None
        else:
            # Buscar la tabla dentro del contenedor principal
            target_table = main_container.find('table', class_='Table')
            if not target_table:
                logger.warning("No se encontró tabla dentro del contenedor principal")
                return None
            logger.info("✅ Tabla encontrada dentro del contenedor principal")
        
        # Buscar fila de promedios (generalmente la última fila)
        rows = target_table.find_all("tr")
        if not rows:
            logger.warning("No se encontraron filas en la tabla")
            return None
        
        # Usar la última fila como promedios
        avg_row = rows[-1]
        logger.info(f"Usando última fila como promedios: {len(avg_row.find_all(['td', 'th']))} celdas")
        
        # Extraer datos de la fila
        stats = parse_team_stats_row(avg_row)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error al extraer estadísticas promedio: {e}")
        return None

def find_averages_row(table):
    """
    Encontrar la fila que contiene los promedios del equipo.
    
    Args:
        table: BeautifulSoup table element
        
    Returns:
        BeautifulSoup tr element o None
    """
    try:
        # Buscar fila con texto "AVG" o "TOTALS"
        rows = table.find_all("tr")
        
        for row in rows:
            row_text = row.get_text().upper()
            if "AVG" in row_text or "TOTALS" in row_text or "AVERAGE" in row_text:
                return row
        
        # Si no se encuentra, usar la última fila
        if rows:
            return rows[-1]
        
        return None
        
    except Exception as e:
        logger.error(f"Error al buscar fila de promedios: {e}")
        return None

def parse_team_stats_row(row):
    """
    Parsear datos de la fila de estadísticas.
    
    Args:
        row: BeautifulSoup tr element
        
    Returns:
        dict: Estadísticas parseadas
    """
    try:
        cells = row.find_all(["td", "th"])
        logger.info(f"Parseando fila con {len(cells)} celdas")
        
        if len(cells) < 10:
            logger.warning(f"Fila con pocas celdas: {len(cells)}")
            return None
        
        # Mostrar contenido de las celdas para debug
        for i, cell in enumerate(cells[:10]):
            text = cell.get_text().strip()
            logger.info(f"  Celda {i}: '{text}'")
        
        # Mapeo de columnas basado en la estructura real de ESPN
        # Columnas: FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, OR, DR, REB, AST, STL, BLK, TO, PF, PTS
        stats = {
            "team_name": "Unknown",
            "season": 2024,
            # Estadísticas básicas
            "fg_pct": parse_stat_value(cells[2].get_text()) if len(cells) > 2 else 0.0,  # FG%
            "threep_pct": parse_stat_value(cells[5].get_text()) if len(cells) > 5 else 0.0,  # 3P%
            "ft_pct": parse_stat_value(cells[8].get_text()) if len(cells) > 8 else 0.0,  # FT%
            "rpg": parse_stat_value(cells[11].get_text()) if len(cells) > 11 else 0.0,  # REB
            "apg": parse_stat_value(cells[12].get_text()) if len(cells) > 12 else 0.0,  # AST
            "spg": parse_stat_value(cells[13].get_text()) if len(cells) > 13 else 0.0,  # STL
            "bpg": parse_stat_value(cells[14].get_text()) if len(cells) > 14 else 0.0,  # BLK
            "tpg": parse_stat_value(cells[15].get_text()) if len(cells) > 15 else 0.0,  # TO
            "ppg": parse_stat_value(cells[17].get_text()) if len(cells) > 17 else 0.0,  # PTS
            "oppg": 0.0,  # Se calculará por separado
            "net_rating": 0.0,  # Se calculará por separado
            # Columnas adicionales para compatibilidad
            "FG%": parse_stat_value(cells[2].get_text()) if len(cells) > 2 else 0.0,
            "3P%": parse_stat_value(cells[5].get_text()) if len(cells) > 5 else 0.0,
            "FT%": parse_stat_value(cells[8].get_text()) if len(cells) > 8 else 0.0,
            "REB": parse_stat_value(cells[11].get_text()) if len(cells) > 11 else 0.0,
            "AST": parse_stat_value(cells[12].get_text()) if len(cells) > 12 else 0.0,
            "STL": parse_stat_value(cells[13].get_text()) if len(cells) > 13 else 0.0,
            "BLK": parse_stat_value(cells[14].get_text()) if len(cells) > 14 else 0.0,
            "TO": parse_stat_value(cells[15].get_text()) if len(cells) > 15 else 0.0,
            "PF": parse_stat_value(cells[16].get_text()) if len(cells) > 16 else 0.0,
            "PTS": parse_stat_value(cells[17].get_text()) if len(cells) > 17 else 0.0
        }
        
        logger.info(f"Estadísticas parseadas: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error al parsear fila de estadísticas: {e}")
        return None

def parse_stat_value(text):
    """
    Parsear valor estadístico desde texto.
    
    Args:
        text (str): Texto de la estadística
        
    Returns:
        float or int: Valor parseado o None si no se puede parsear
    """
    try:
        # Limpiar texto
        clean_text = text.strip().replace("%", "")
        
        # Si está vacío, retornar None
        if not clean_text or clean_text == "-":
            return None
        
        # Si es porcentaje, convertir a float
        if "%" in text:
            return float(clean_text) if clean_text else None
        
        # Si es número entero, convertir a int
        if clean_text.replace(".", "").isdigit():
            if "." in clean_text:
                return float(clean_text)
            else:
                return int(clean_text)
        
        return None
        
    except Exception as e:
        logger.debug(f"Error al parsear valor '{text}': {e}")
        return None

def save_team_stats_to_csv(team_stats, team_abbrev):
    """
    Guardar estadísticas de equipo en data/raw/team_stats/{team}.csv.
    
    Args:
        team_stats (dict): Estadísticas del equipo
        team_abbrev (str): Abreviación del equipo
    """
    try:
        # Crear directorio si no existe
        os.makedirs("data/raw/team_stats", exist_ok=True)
        
        # Crear DataFrame
        df = pd.DataFrame([team_stats])
        
        # Guardar CSV
        csv_path = f"data/raw/team_stats/{team_abbrev}.csv"
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Estadísticas de equipo guardadas en {csv_path}")
        
    except Exception as e:
        logger.error(f"Error al guardar estadísticas de {team_abbrev}: {e}")

def scrape_all_teams_stats():
    """
    Scrapear estadísticas de todos los equipos NBA.
    """
    # Lista de equipos NBA (abreviación, nombre)
    teams = [
        ("atl", "atlanta-hawks"),
        ("bos", "boston-celtics"),
        ("bkn", "brooklyn-nets"),
        ("cha", "charlotte-hornets"),
        ("chi", "chicago-bulls"),
        ("cle", "cleveland-cavaliers"),
        ("dal", "dallas-mavericks"),
        ("den", "denver-nuggets"),
        ("det", "detroit-pistons"),
        ("gs", "golden-state-warriors"),
        ("hou", "houston-rockets"),
        ("ind", "indiana-pacers"),
        ("lac", "los-angeles-clippers"),
        ("lal", "los-angeles-lakers"),
        ("mem", "memphis-grizzlies"),
        ("mia", "miami-heat"),
        ("mil", "milwaukee-bucks"),
        ("min", "minnesota-timberwolves"),
        ("no", "new-orleans-pelicans"),
        ("ny", "new-york-knicks"),
        ("okc", "oklahoma-city-thunder"),
        ("orl", "orlando-magic"),
        ("phi", "philadelphia-76ers"),
        ("phx", "phoenix-suns"),
        ("por", "portland-trail-blazers"),
        ("sac", "sacramento-kings"),
        ("sa", "san-antonio-spurs"),
        ("tor", "toronto-raptors"),
        ("utah", "utah-jazz"),
        ("wsh", "washington-wizards")
    ]
    
    logger.info(f"Iniciando scraping de estadísticas para {len(teams)} equipos")
    
    for team_abbrev, team_name in teams:
        logger.info(f"Procesando {team_name}...")
        
        team_stats = scrape_team_stats(team_abbrev, team_name)
        
        if team_stats:
            save_team_stats_to_csv(team_stats, team_abbrev)
        else:
            logger.warning(f"No se pudieron obtener estadísticas para {team_name}")
    
    logger.info("Scraping de estadísticas de equipos completado")
