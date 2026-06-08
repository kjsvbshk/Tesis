"""
Utilidades comunes para todos los scrapers
"""

import requests
from bs4 import BeautifulSoup
from loguru import logger

def get_espn_headers():
    """
    Headers HTTP estándar para ESPN.
    
    Returns:
        dict: Headers HTTP
    """
    return {
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

def fetch_espn_page(url, timeout=30):
    """
    Hacer petición HTTP a ESPN con headers estándar.
    
    Args:
        url (str): URL a scrapear
        timeout (int): Timeout en segundos
        
    Returns:
        BeautifulSoup: Objeto soup parseado o None si hay error
    """
    try:
        headers = get_espn_headers()
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    except requests.RequestException as e:
        logger.error(f"Error de conexión al obtener {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al procesar {url}: {e}")
        return None

def parse_numeric_value(text):
    """
    Parsear valor numérico.
    
    Args:
        text (str): Texto a parsear
        
    Returns:
        int: Valor numérico o 0
    """
    try:
        clean_text = str(text).strip()
        if clean_text.isdigit():
            return int(clean_text)
        return 0
    except:
        return 0

def parse_percentage_value(text):
    """
    Parsear valor de porcentaje.
    
    Args:
        text (str): Texto a parsear
        
    Returns:
        float: Porcentaje como decimal o 0.0
    """
    try:
        clean_text = str(text).strip().replace("%", "")
        if clean_text and clean_text.replace(".", "").isdigit():
            return float(clean_text)
        return 0.0
    except:
        return 0.0

def parse_games_behind(text):
    """
    Parsear valor de juegos detrás.
    
    Args:
        text (str): Texto a parsear
        
    Returns:
        int: Juegos detrás o 0
    """
    try:
        clean_text = str(text).strip()
        if clean_text == '-' or clean_text == '':
            return 0
        if clean_text.isdigit():
            return int(clean_text)
        return 0
    except:
        return 0

def parse_stat_value(text):
    """
    Parsear valor estadístico desde texto.
    
    Args:
        text (str): Texto de la estadística
        
    Returns:
        float or int: Valor parseado o None si no se puede parsear
    """
    try:
        clean_text = str(text).strip().replace("%", "")
        
        if not clean_text or clean_text == "-":
            return None
        
        if "%" in str(text):
            return float(clean_text) if clean_text else None
        
        if clean_text.replace(".", "").isdigit():
            if "." in clean_text:
                return float(clean_text)
            else:
                return int(clean_text)
        
        return None
    except:
        return None
