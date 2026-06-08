"""
Script final para scrapear player boxscores usando el mapping ESPN -> NBA.com

Este script se ejecuta DESPUÉS de scrape_and_match_schedule.py
"""

import json
import os
import time
from loguru import logger
from tqdm import tqdm
from pathlib import Path

# Importar scraper
from nba_com.player_boxscore_scraper import scrape_player_boxscore

def load_mapping(mapping_file='data/espn_to_nba_mapping.json'):
    if not os.path.exists(mapping_file):
        logger.error(f"Mapping file not found: {mapping_file}")
        return {}
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def scrape_players_using_mapping(mapping, output_dir='data/raw/nba_com_players', delay=1.5):
    """
    Scrapear player data usando el mapping
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Filtrar ya scrapeados
    existing_files = set(f.stem for f in Path(output_dir).glob('*.json'))
    
    # Crear lista de tareas (excluyendo ya scrapeados)
    tasks = []
    for espn_id, nba_id in mapping.items():
        # Usamos nba_id como nombre de archivo
        if nba_id not in existing_files:
            tasks.append({'espn_id': espn_id, 'nba_id': nba_id})
    
    logger.info(f"Total juegos mapeados: {len(mapping)}")
    logger.info(f"Ya scrapeados: {len(existing_files)}")
    logger.info(f"Pendientes: {len(tasks)}")
    
    successful = 0
    failed = 0
    empty_data = 0
    
    pbar = tqdm(tasks, desc="Scrapeando players")
    
    for task in pbar:
        espn_id = task['espn_id']
        nba_id = task['nba_id']
        
        # Retry logic
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Scrapear usando NBA ID
                result = scrape_player_boxscore(nba_id)
                
                if result:
                    # Validar contenido
                    total_players = len(result['away_players']) + len(result['home_players'])
                    
                    if total_players == 0:
                        logger.warning(f"⚠️  Datos vacíos para {nba_id} (ESPN: {espn_id}) - Intento {attempt+1}/{max_retries}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                        empty_data += 1
                        break
                    
                    # Agregar referencia a ESPN ID
                    result['espn_game_id'] = espn_id
                    
                    # Guardar
                    filename = f"{output_dir}/{nba_id}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    
                    successful += 1
                    pbar.set_description(f"✅ {nba_id}")
                    break # Éxito, salir del loop de retries
                    
                else:
                    logger.warning(f"❌ Falló scraping para {nba_id} - Intento {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    failed += 1
                    pbar.set_description(f"❌ {nba_id}")
                
            except KeyboardInterrupt:
                logger.warning("Interrumpido por usuario")
                return # Salir completamente
            except Exception as e:
                logger.error(f"Error en {nba_id}: {e} - Intento {attempt+1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                failed += 1
        
        time.sleep(delay)
    
    print(f"\n{'='*80}")
    print(f"RESUMEN FINAL")
    print(f"{'='*80}")
    print(f"✅ Exitosos: {successful}")
    print(f"❌ Fallidos: {failed}")
    print(f"⚠️  Vacíos (no guardados): {empty_data}")
    print(f"💾 Directorio: {output_dir}")

if __name__ == '__main__':
    mapping = load_mapping()
    
    if mapping:
        scrape_players_using_mapping(mapping)
    else:
        print("No se encontró mapping. Ejecuta primero scrape_and_match_schedule.py")
