#!/usr/bin/env python3
"""
Script para ejecutar todos los scrapers de Premier League en orden.
"""

import sys
import os
from datetime import datetime
from loguru import logger

# Agregar utils al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.logger import setup_logger

# Configurar logger
setup_logger()

def run_standings_scraper(season="2024"):
    """Ejecutar scraper de clasificaciones"""
    logger.info("=" * 80)
    logger.info("EJECUTANDO SCRAPER DE CLASIFICACIONES")
    logger.info("=" * 80)
    
    try:
        from espn.standings_scraper import scrape_standings, save_standings_to_csv
        
        standings_data = scrape_standings(season=season)
        
        if standings_data:
            save_standings_to_csv(standings_data, season=season)
            logger.info(f"✓ Clasificaciones scrapeadas exitosamente: {len(standings_data)} equipos")
            return True
        else:
            logger.error("✗ No se pudieron obtener las clasificaciones")
            return False
    except Exception as e:
        logger.error(f"✗ Error ejecutando scraper de clasificaciones: {e}")
        return False


def run_team_stats_scraper(season="2024"):
    """Ejecutar scraper de estadísticas de equipos"""
    logger.info("=" * 80)
    logger.info("EJECUTANDO SCRAPER DE ESTADÍSTICAS DE EQUIPOS")
    logger.info("=" * 80)
    
    try:
        from espn.team_stats_scraper import scrape_all_teams_stats, save_team_stats_to_csv
        
        df = scrape_all_teams_stats(season=season)
        
        if df is not None and len(df) > 0:
            save_team_stats_to_csv(df, season=season)
            logger.info(f"✓ Estadísticas de equipos scrapeadas exitosamente: {len(df)} equipos")
            return True
        else:
            logger.error("✗ No se pudieron obtener estadísticas de equipos")
            return False
    except Exception as e:
        logger.error(f"✗ Error ejecutando scraper de estadísticas de equipos: {e}")
        return False


def run_match_stats_scraper(season="2024"):
    """Ejecutar scraper de estadísticas de partidos"""
    logger.info("=" * 80)
    logger.info("EJECUTANDO SCRAPER DE ESTADÍSTICAS DE PARTIDOS")
    logger.info("=" * 80)
    
    try:
        from espn.match_stats_scraper import scrape_matches_from_season, save_match_stats_to_csv
        
        df = scrape_matches_from_season(season=season)
        
        if df is not None and len(df) > 0:
            save_match_stats_to_csv(df, season=season)
            logger.info(f"✓ Estadísticas de partidos scrapeadas exitosamente: {len(df)} partidos")
            return True
        else:
            logger.warning("⚠ No se pudieron obtener estadísticas de partidos (puede requerir match_ids)")
            return False
    except Exception as e:
        logger.error(f"✗ Error ejecutando scraper de estadísticas de partidos: {e}")
        return False


def run_player_stats_scraper(season="2024"):
    """Ejecutar scraper de estadísticas de jugadores"""
    logger.info("=" * 80)
    logger.info("EJECUTANDO SCRAPER DE ESTADÍSTICAS DE JUGADORES")
    logger.info("=" * 80)
    
    try:
        from espn.player_stats_scraper import scrape_all_player_stats, save_player_stats_to_csv
        
        df = scrape_all_player_stats(season=season, categories=["goals", "assists"], limit=50)
        
        if df is not None and len(df) > 0:
            save_player_stats_to_csv(df, season=season)
            logger.info(f"✓ Estadísticas de jugadores scrapeadas exitosamente: {len(df)} jugadores")
            return True
        else:
            logger.warning("⚠ No se pudieron obtener estadísticas de jugadores")
            return False
    except Exception as e:
        logger.error(f"✗ Error ejecutando scraper de estadísticas de jugadores: {e}")
        return False


def run_injuries_scraper():
    """Ejecutar scraper de lesiones"""
    logger.info("=" * 80)
    logger.info("EJECUTANDO SCRAPER DE LESIONES")
    logger.info("=" * 80)
    
    try:
        from espn.injuries_scraper import scrape_injuries, save_injuries_to_csv
        
        injuries_data = scrape_injuries()
        
        if injuries_data:
            save_injuries_to_csv(injuries_data)
            logger.info(f"✓ Lesiones scrapeadas exitosamente: {len(injuries_data)} jugadores")
            return True
        else:
            logger.warning("⚠ No se pudieron obtener datos de lesiones")
            return False
    except Exception as e:
        logger.error(f"✗ Error ejecutando scraper de lesiones: {e}")
        return False


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Ejecutar todos los scrapers de Premier League'
    )
    
    parser.add_argument(
        '--season',
        type=str,
        default='2024',
        help='Temporada a scrapear (ej: "2024")'
    )
    
    parser.add_argument(
        '--skip-standings',
        action='store_true',
        help='Saltar scraper de clasificaciones'
    )
    
    parser.add_argument(
        '--skip-team-stats',
        action='store_true',
        help='Saltar scraper de estadísticas de equipos'
    )
    
    parser.add_argument(
        '--skip-match-stats',
        action='store_true',
        help='Saltar scraper de estadísticas de partidos'
    )
    
    parser.add_argument(
        '--skip-player-stats',
        action='store_true',
        help='Saltar scraper de estadísticas de jugadores'
    )
    
    parser.add_argument(
        '--skip-injuries',
        action='store_true',
        help='Saltar scraper de lesiones'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("INICIANDO SCRAPING COMPLETO DE PREMIER LEAGUE")
    logger.info(f"Temporada: {args.season}")
    logger.info("=" * 80)
    logger.info("")
    
    results = {}
    
    # Ejecutar scrapers
    if not args.skip_standings:
        results['standings'] = run_standings_scraper(args.season)
        logger.info("")
    
    if not args.skip_team_stats:
        results['team_stats'] = run_team_stats_scraper(args.season)
        logger.info("")
    
    if not args.skip_match_stats:
        results['match_stats'] = run_match_stats_scraper(args.season)
        logger.info("")
    
    if not args.skip_player_stats:
        results['player_stats'] = run_player_stats_scraper(args.season)
        logger.info("")
    
    if not args.skip_injuries:
        results['injuries'] = run_injuries_scraper()
        logger.info("")
    
    # Resumen final
    logger.info("=" * 80)
    logger.info("RESUMEN DE SCRAPING")
    logger.info("=" * 80)
    
    for scraper, success in results.items():
        status = "✓ EXITOSO" if success else "✗ FALLIDO"
        logger.info(f"  {scraper}: {status}")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("SCRAPING COMPLETADO")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()


