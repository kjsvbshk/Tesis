import requests
import json
import os
from datetime import datetime
from loguru import logger

def scrape_odds(date=None):
    """
    Extraer cuotas de apuestas NBA desde The Odds API.
    
    Args:
        date (str): Fecha en formato YYYY-MM-DD. Si None, usa fecha actual.
        
    Returns:
        dict: Datos de cuotas o None si hay error
    """
    # API Key de The Odds API
    api_key = "e123f1c13b19f4cdc29d9393c978ec4e"
    
    # URL de la API
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds?regions=us&markets=h2h&apiKey={api_key}"
    
    try:
        res = requests.get(url)
        res.raise_for_status()
        
        odds_data = res.json()
        
        if odds_data:
            logger.info(f"Cuotas extraídas exitosamente: {len(odds_data)} partidos")
            return odds_data
        else:
            logger.warning("No se encontraron datos de cuotas")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error de conexión al obtener cuotas: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear JSON de cuotas: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al procesar cuotas: {e}")
        return None

def process_odds_data(odds_data):
    """
    Procesar y limpiar datos de cuotas.
    
    Args:
        odds_data (list): Datos raw de la API
        
    Returns:
        list: Lista de diccionarios con cuotas procesadas
    """
    try:
        processed_odds = []
        
        for game in odds_data:
            processed_game = process_single_game(game)
            if processed_game:
                processed_odds.append(processed_game)
        
        return processed_odds
        
    except Exception as e:
        logger.error(f"Error al procesar datos de cuotas: {e}")
        return []

def process_single_game(game_data):
    """
    Procesar datos de un juego individual.
    
    Args:
        game_data (dict): Datos de un juego
        
    Returns:
        dict: Datos procesados del juego o None
    """
    try:
        # Extraer información básica del juego
        game_info = {
            "game_id": game_data.get("id"),
            "sport_key": game_data.get("sport_key"),
            "sport_title": game_data.get("sport_title"),
            "commence_time": game_data.get("commence_time"),
            "home_team": game_data.get("home_team"),
            "away_team": game_data.get("away_team")
        }
        
        # Procesar cuotas de diferentes casas de apuestas
        bookmakers = []
        for bookmaker in game_data.get("bookmakers", []):
            bookmaker_data = process_bookmaker(bookmaker)
            if bookmaker_data:
                bookmakers.append(bookmaker_data)
        
        game_info["bookmakers"] = bookmakers
        
        return game_info
        
    except Exception as e:
        logger.error(f"Error al procesar juego individual: {e}")
        return None

def process_bookmaker(bookmaker_data):
    """
    Procesar datos de una casa de apuestas.
    
    Args:
        bookmaker_data (dict): Datos de la casa de apuestas
        
    Returns:
        dict: Datos procesados de la casa de apuestas
    """
    try:
        bookmaker_info = {
            "key": bookmaker_data.get("key"),
            "title": bookmaker_data.get("title"),
            "last_update": bookmaker_data.get("last_update"),
            "markets": []
        }
        
        # Procesar mercados (h2h - head to head)
        for market in bookmaker_data.get("markets", []):
            market_data = process_market(market)
            if market_data:
                bookmaker_info["markets"].append(market_data)
        
        return bookmaker_info
        
    except Exception as e:
        logger.error(f"Error al procesar casa de apuestas: {e}")
        return None

def process_market(market_data):
    """
    Procesar datos de un mercado de apuestas.
    
    Args:
        market_data (dict): Datos del mercado
        
    Returns:
        dict: Datos procesados del mercado
    """
    try:
        market_info = {
            "key": market_data.get("key"),
            "last_update": market_data.get("last_update"),
            "outcomes": []
        }
        
        # Procesar resultados/opciones
        for outcome in market_data.get("outcomes", []):
            outcome_data = {
                "name": outcome.get("name"),
                "price": outcome.get("price"),
                "point": outcome.get("point")
            }
            market_info["outcomes"].append(outcome_data)
        
        return market_info
        
    except Exception as e:
        logger.error(f"Error al procesar mercado: {e}")
        return None

def save_odds_to_json(odds_data, date=None):
    """
    Guardar cuotas en data/raw/odds/{date}.json.
    
    Args:
        odds_data (list): Datos de cuotas
        date (str): Fecha en formato YYYY-MM-DD
    """
    try:
        # Crear directorio si no existe
        os.makedirs("data/raw/odds", exist_ok=True)
        
        # Determinar fecha
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Guardar JSON
        json_path = f"data/raw/odds/{date}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(odds_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Cuotas guardadas en {json_path}")
        logger.info(f"Total de partidos con cuotas: {len(odds_data)}")
        
    except Exception as e:
        logger.error(f"Error al guardar cuotas: {e}")

def scrape_current_odds():
    """
    Scrapear cuotas actuales.
    """
    logger.info("Iniciando scraping de cuotas actuales")
    
    # Obtener datos raw de la API
    raw_odds_data = scrape_odds()
    
    if raw_odds_data:
        # Procesar datos
        processed_odds = process_odds_data(raw_odds_data)
        
        if processed_odds:
            save_odds_to_json(processed_odds)
            logger.info("Scraping de cuotas completado")
        else:
            logger.error("No se pudieron procesar las cuotas")
    else:
        logger.error("No se pudieron obtener las cuotas")

def get_odds_summary(odds_data):
    """
    Obtener resumen de cuotas para análisis.
    
    Args:
        odds_data (list): Datos de cuotas procesadas
        
    Returns:
        dict: Resumen de cuotas
    """
    try:
        summary = {
            "total_games": len(odds_data),
            "total_bookmakers": 0,
            "games_with_odds": 0,
            "average_odds": {},
            "bookmaker_coverage": {}
        }
        
        total_home_odds = 0
        total_away_odds = 0
        games_with_odds = 0
        
        for game in odds_data:
            if game.get("bookmakers"):
                games_with_odds += 1
                summary["total_bookmakers"] += len(game["bookmakers"])
                
                # Calcular promedios de cuotas
                for bookmaker in game["bookmakers"]:
                    for market in bookmaker.get("markets", []):
                        if market["key"] == "h2h":
                            for outcome in market.get("outcomes", []):
                                if outcome.get("name") == game.get("home_team"):
                                    total_home_odds += float(outcome.get("price", 0))
                                elif outcome.get("name") == game.get("away_team"):
                                    total_away_odds += float(outcome.get("price", 0))
        
        summary["games_with_odds"] = games_with_odds
        
        if games_with_odds > 0:
            summary["average_odds"] = {
                "home_team": round(total_home_odds / games_with_odds, 2),
                "away_team": round(total_away_odds / games_with_odds, 2)
            }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error al generar resumen de cuotas: {e}")
        return {}
