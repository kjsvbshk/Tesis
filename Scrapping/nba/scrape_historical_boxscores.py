#!/usr/bin/env python3
"""
Scraper de Boxscores Históricos NBA
====================================

Script para scrapear boxscores de temporadas completas históricas.

Uso:
    python scrape_historical_boxscores.py --season "2023-24" --type "regular"
    python scrape_historical_boxscores.py --season "2023-24" --type "playoffs"
    python scrape_historical_boxscores.py --season "2024-25" --type "regular"
    python scrape_historical_boxscores.py --season "2024-25" --type "playoffs"
    python scrape_historical_boxscores.py --season "2025-26" --type "regular"
"""

import argparse
import sys
from loguru import logger
from espn.espn_schedule_scraper import scrape_season_game_ids
from espn.espn_scraper import scrape_boxscore, save_boxscore_to_json
import pandas as pd
import time

# Configurar logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
logger.add("logs/historical_boxscores_{time}.log", rotation="1 day", retention="7 days", encoding="utf-8")

# Mapeo de temporadas a rangos de fechas
SEASON_DATE_RANGES = {
    "2023-24": {
        "regular": {"start": "20231024", "end": "20240414"},
        "playoffs": {"start": "20240416", "end": "20240617"}
    },
    "2024-25": {
        "regular": {"start": "20241022", "end": "20250413"},
        "playoffs": {"start": "20250419", "end": "20250622"}
    },
    "2025-26": {
        "regular": {"start": "20251021", "end": "20260412"},
        "playoffs": {"start": "20260418", "end": "20260621"}
    }
}

def scrape_historical_season(season: str, season_type: str):
    """
    Scrapear boxscores de una temporada histórica completa
    
    Args:
        season: Temporada (ej: "2023-24")
        season_type: Tipo ("regular" o "playoffs")
    """
    
    logger.info("="*80)
    logger.info(f"SCRAPING DE BOXSCORES HISTORICOS - {season} {season_type.upper()}")
    logger.info("="*80)
    
    if season not in SEASON_DATE_RANGES:
        logger.error(f"Temporada no soportada: {season}")
        return
    
    if season_type not in SEASON_DATE_RANGES[season]:
        logger.error(f"Tipo de temporada no soportado: {season_type}")
        return
    
    # Obtener rango de fechas
    date_range = SEASON_DATE_RANGES[season][season_type]
    start_date = date_range["start"]
    end_date = date_range["end"]
    
    logger.info(f"Rango de fechas: {start_date} - {end_date}")
    
    # PASO 1: Obtener todos los game IDs de la temporada
    logger.info("\n[PASO 1/2] Obteniendo game IDs...")
    scrape_season_game_ids(start_date, end_date)
    
    # PASO 2: Leer game IDs del CSV y scrapear boxscores
    logger.info("\n[PASO 2/2] Scrapeando boxscores...")
    
    try:
        # Leer game IDs
        df_game_ids = pd.read_csv("data/raw/game_ids.csv")
        total_games = len(df_game_ids)
        logger.info(f"Total de partidos a scrapear: {total_games}")
        
        # Scrapear cada boxscore
        successful = 0
        failed = 0
        
        for idx, row in df_game_ids.iterrows():
            game_id = row['game_id']
            game_date = row['date']
            
            logger.info(f"\n[{idx+1}/{total_games}] Scrapeando game_id: {game_id} (fecha: {game_date})")
            
            # Scrapear boxscore
            game_data = scrape_boxscore(game_id)
            
            if game_data:
                # Guardar en JSON
                save_boxscore_to_json(game_data, game_id)
                successful += 1
            else:
                logger.warning(f"   [WARN] No se pudo scrapear game_id: {game_id}")
                failed += 1
            
            # Delay para no sobrecargar el servidor
            if (idx + 1) % 10 == 0:
                logger.info(f"   [PROGRESS] {idx+1}/{total_games} completados ({successful} exitosos, {failed} fallidos)")
                time.sleep(2)  # Pausa de 2 segundos cada 10 partidos
            else:
                time.sleep(0.5)  # Pausa corta entre requests
        
        # Resumen final
        logger.info("\n" + "="*80)
        logger.info("RESUMEN DE SCRAPING")
        logger.info("="*80)
        logger.info(f"Total de partidos: {total_games}")
        logger.info(f"Exitosos: {successful}")
        logger.info(f"Fallidos: {failed}")
        logger.info(f"Tasa de éxito: {(successful/total_games)*100:.1f}%")
        logger.info("="*80)
        
    except FileNotFoundError:
        logger.error("No se encontró el archivo data/raw/game_ids.csv")
        logger.error("Asegúrate de que el Paso 1 se haya completado correctamente")
    except Exception as e:
        logger.error(f"Error durante scraping: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Scraper de boxscores históricos NBA'
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
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Ejecutar scraping
    scrape_historical_season(args.season, args.type)

if __name__ == "__main__":
    main()
