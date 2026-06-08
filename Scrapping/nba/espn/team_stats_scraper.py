#!/usr/bin/env python3
"""
ESPN Team Stats Scraper
========================

Scraper de estadísticas de equipos NBA por temporada.
Extrae estadísticas de todos los equipos para temporadas específicas.

Uso:
    python -m espn.team_stats_scraper --season "2023-24" --type "regular"
    python -m espn.team_stats_scraper --season "2023-24" --type "playoffs"
    python -m espn.team_stats_scraper --season "2024-25" --type "regular"
    python -m espn.team_stats_scraper --season "2024-25" --type "playoffs"
"""

import argparse
import sys
from loguru import logger
from espn.team_scraper import scrape_all_teams_stats

# Configurar logger (sin emojis para evitar problemas de encoding)
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
logger.add("logs/team_stats_scraper_{time}.log", rotation="1 day", retention="7 days", encoding="utf-8")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Scraper de estadísticas de equipos NBA'
    )
    parser.add_argument(
        '--season',
        type=str,
        required=True,
        help='Temporada (ej: "2023-24", "2024-25")'
    )
    parser.add_argument(
        '--type',
        type=str,
        choices=['regular', 'playoffs'],
        default='regular',
        help='Tipo de temporada: regular o playoffs'
    )
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("SCRAPING DE ESTADISTICAS DE EQUIPOS NBA")
    logger.info(f"   Temporada: {args.season}")
    logger.info(f"   Tipo: {args.type.upper()}")
    logger.info("="*80 + "\n")
    
    # Ejecutar scraping
    scrape_all_teams_stats(season=args.season, season_type=args.type)
    
    logger.info("\n" + "="*80)
    logger.info("SCRAPING COMPLETADO")
    logger.info("="*80)

if __name__ == "__main__":
    main()

