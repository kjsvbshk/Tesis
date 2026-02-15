"""
Script para ejecutar SOLO el matching y luego el scraping de jugadores.
Usa el schedule ya scrapeado en data/nba_com_schedule.json
"""

import json
import os
from loguru import logger
from tqdm import tqdm
from pathlib import Path
import time
import sys

# Asegurar que el directorio actual está en el path para importar
sys.path.append(os.getcwd())

# Importar funciones necesarias (ahora cargará la versión actualizada)
from scrape_and_match_schedule import load_espn_games, match_games
from scrape_players_from_mapping import scrape_players_using_mapping

def run_process():
    # 1. Cargar Schedule NBA existente
    schedule_path = 'data/nba_com_schedule.json'
    logger.info(f"Cargando schedule desde {schedule_path}...")
    
    if not os.path.exists(schedule_path):
        logger.error("No existe el archivo de schedule. Ejecuta scrape_and_match_schedule.py primero.")
        return

    with open(schedule_path, 'r', encoding='utf-8') as f:
        nba_games = json.load(f)
    
    logger.info(f"✅ Schedule cargado: {len(nba_games)} partidos")

    # 2. Cargar juegos ESPN
    logger.info("Cargando juegos de ESPN...")
    espn_games = load_espn_games()
    logger.info(f"✅ Juegos ESPN cargados: {len(espn_games)}")

    # 3. Ejecutar Matching
    logger.info("Ejecutando matching (Teams + Scores + Inverted)...")
    mapping, unmatched = match_games(nba_games, espn_games)
    
    # Reporte de cobertura
    total_espn = len(espn_games)
    matched_count = len(mapping)
    coverage = matched_count/total_espn*100
    
    logger.info(f"📊 COBERTURA FINAL: {matched_count}/{total_espn} ({coverage:.1f}%)")
    
    # Guardar mapping
    with open('data/espn_to_nba_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)
    logger.info(f"💾 Mapping guardado: data/espn_to_nba_mapping.json")

    # Guardar unmatched
    if unmatched:
        with open('data/unmatched_espn_games.json', 'w', encoding='utf-8') as f:
            json.dump(unmatched, f, indent=2)
        logger.warning(f"⚠️ Juegos sin match: {len(unmatched)}")

    # 4. Iniciar Scraping de Jugadores (Batch Final)
    logger.info("Iniciando scraping de jugadores (Batch Final)...")
    scrape_players_using_mapping(mapping)

if __name__ == '__main__':
    run_process()
