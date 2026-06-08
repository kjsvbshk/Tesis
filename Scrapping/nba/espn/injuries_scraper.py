import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime
from loguru import logger

def scrape_injuries(date=None):
    """
    Extraer reportes de lesiones de jugadores NBA.
    
    Args:
        date (str): Fecha en formato YYYY-MM-DD. Si None, usa fecha actual.
        
    Returns:
        list: Lista de diccionarios con datos de lesiones
    """
    url = "https://www.espn.com/nba/injuries"
    
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
        
        # Extraer datos de lesiones
        injuries_data = extract_injuries_data(soup)
        
        if injuries_data:
            logger.info(f"Reportes de lesiones extraídos exitosamente: {len(injuries_data)} jugadores")
            return injuries_data
        else:
            logger.warning("No se encontraron datos de lesiones")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error de conexión al obtener reportes de lesiones: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al procesar reportes de lesiones: {e}")
        return None

def extract_injuries_data(soup):
    """
    Extraer datos de lesiones desde el HTML.
    
    Args:
        soup: BeautifulSoup object del HTML
        
    Returns:
        list: Lista de diccionarios con datos de lesiones
    """
    try:
        injuries = []
        
        # Buscar contenedores de lesiones por equipo
        injury_containers = soup.find_all("div", class_="ResponsiveTable")
        
        for container in injury_containers:
            # Extraer nombre del equipo
            team_name = extract_team_name_from_container(container)
            
            # Extraer lesiones del equipo
            team_injuries = extract_team_injuries(container, team_name)
            injuries.extend(team_injuries)
        
        return injuries
        
    except Exception as e:
        logger.error(f"Error al extraer datos de lesiones: {e}")
        return None

def extract_team_name_from_container(container):
    """
    Extraer nombre del equipo desde el contenedor.
    
    Args:
        container: BeautifulSoup div element
        
    Returns:
        str: Nombre del equipo o None
    """
    try:
        # Buscar título o encabezado del equipo
        title_element = container.find("h2") or container.find("h3")
        if title_element:
            return title_element.get_text().strip()
        
        # Buscar en el texto del contenedor
        container_text = container.get_text()
        # Buscar patrones comunes de nombres de equipos
        team_keywords = [
            "Celtics", "Lakers", "Warriors", "Bulls", "Heat", "Spurs", "Knicks",
            "Nets", "76ers", "Raptors", "Bucks", "Pacers", "Cavaliers", "Pistons",
            "Hawks", "Hornets", "Magic", "Wizards", "Mavericks", "Rockets", "Grizzlies",
            "Pelicans", "Suns", "Jazz", "Nuggets", "Trail Blazers", "Kings", "Thunder",
            "Timberwolves", "Clippers"
        ]
        
        for keyword in team_keywords:
            if keyword in container_text:
                return keyword
        
        return "Unknown Team"
        
    except:
        return "Unknown Team"

def extract_team_injuries(container, team_name):
    """
    Extraer lesiones de un equipo específico.
    
    Args:
        container: BeautifulSoup div element
        team_name (str): Nombre del equipo
        
    Returns:
        list: Lista de diccionarios con lesiones del equipo
    """
    try:
        team_injuries = []
        
        # Buscar tabla de lesiones
        table = container.find("table")
        if not table:
            return team_injuries
        
        # Extraer filas de jugadores lesionados
        rows = table.find_all("tr")
        
        for row in rows:
            # Saltar fila de encabezado
            if is_injury_header_row(row):
                continue
            
            injury_data = parse_injury_row(row, team_name)
            if injury_data:
                team_injuries.append(injury_data)
        
        return team_injuries
        
    except Exception as e:
        logger.error(f"Error al extraer lesiones del equipo {team_name}: {e}")
        return []

def is_injury_header_row(row):
    """
    Verificar si la fila es un encabezado.
    
    Args:
        row: BeautifulSoup tr element
        
    Returns:
        bool: True si es encabezado
    """
    try:
        row_text = row.get_text().upper()
        header_keywords = ["PLAYER", "POSITION", "STATUS", "DATE", "INJURY"]
        
        return any(keyword in row_text for keyword in header_keywords)
    except:
        return False

def parse_injury_row(row, team_name):
    """
    Parsear datos de una fila de lesión.
    
    Args:
        row: BeautifulSoup tr element
        team_name (str): Nombre del equipo
        
    Returns:
        dict: Datos de la lesión o None si no es válido
    """
    try:
        cells = row.find_all("td")
        
        if len(cells) < 4:
            return None
        
        # Extraer datos de la lesión
        injury_data = {
            "Team": team_name,
            "Player": extract_player_name(cells[0]) if len(cells) > 0 else None,
            "Position": extract_position(cells[1]) if len(cells) > 1 else None,
            "Status": extract_status(cells[2]) if len(cells) > 2 else None,
            "Description": extract_description(cells[3]) if len(cells) > 3 else None
        }
        
        # Solo incluir si tiene al menos jugador y estado
        if injury_data["Player"] and injury_data["Status"]:
            return injury_data
        
        return None
        
    except Exception as e:
        logger.error(f"Error al parsear fila de lesión: {e}")
        return None

def extract_player_name(cell):
    """
    Extraer nombre del jugador desde la celda.
    
    Args:
        cell: BeautifulSoup td element
        
    Returns:
        str: Nombre del jugador o None
    """
    try:
        # Buscar enlace del jugador
        link = cell.find("a")
        if link:
            return link.get_text().strip()
        
        # Buscar texto directo
        text = cell.get_text().strip()
        if text and not text.isdigit():
            return text
        
        return None
        
    except:
        return None

def extract_position(cell):
    """
    Extraer posición del jugador.
    
    Args:
        cell: BeautifulSoup td element
        
    Returns:
        str: Posición o None
    """
    try:
        text = cell.get_text().strip()
        if text and text in ["PG", "SG", "SF", "PF", "C", "G", "F"]:
            return text
        return None
    except:
        return None

def extract_status(cell):
    """
    Extraer estado de la lesión.
    
    Args:
        cell: BeautifulSoup td element
        
    Returns:
        str: Estado o None
    """
    try:
        text = cell.get_text().strip()
        if text:
            return text
        return None
    except:
        return None

def extract_description(cell):
    """
    Extraer descripción de la lesión.
    
    Args:
        cell: BeautifulSoup td element
        
    Returns:
        str: Descripción o None
    """
    try:
        text = cell.get_text().strip()
        if text:
            return text
        return None
    except:
        return None

def save_injuries_to_csv(injuries_data, date=None):
    """
    Guardar reportes de lesiones en data/raw/injuries/{date}.csv.
    
    Args:
        injuries_data (list): Datos de lesiones
        date (str): Fecha en formato YYYY-MM-DD
    """
    try:
        # Crear directorio si no existe
        os.makedirs("data/raw/injuries", exist_ok=True)
        
        # Determinar fecha
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Crear DataFrame
        df = pd.DataFrame(injuries_data)
        
        # Guardar CSV
        csv_path = f"data/raw/injuries/{date}.csv"
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Reportes de lesiones guardados en {csv_path}")
        logger.info(f"Total de jugadores lesionados: {len(df)}")
        
    except Exception as e:
        logger.error(f"Error al guardar reportes de lesiones: {e}")

def scrape_current_injuries():
    """
    Scrapear reportes de lesiones actuales.
    """
    logger.info("Iniciando scraping de reportes de lesiones actuales")
    
    injuries_data = scrape_injuries()
    
    if injuries_data:
        save_injuries_to_csv(injuries_data)
        logger.info("Scraping de reportes de lesiones completado")
    else:
        logger.error("No se pudieron obtener los reportes de lesiones")
