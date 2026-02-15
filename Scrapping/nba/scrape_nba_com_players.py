"""
Script para scrapear player boxscores de NBA.com para todos los partidos

Proceso:
1. Leer todos los game_ids de ESPN (desde data/raw/boxscores/)
2. Mapear team names → team slugs
3. Scrapear cada partido con rate limiting
4. Guardar en data/raw/nba_com_players/
"""

import os
import json
import time
from pathlib import Path
from loguru import logger
from tqdm import tqdm
import sys

# Importar scraper y team slugs
sys.path.append(os.path.dirname(__file__))
from nba_com.player_boxscore_scraper import scrape_player_boxscore, save_player_boxscore
from nba_com.team_slugs import get_team_slug

def load_espn_boxscores(boxscores_dir='data/raw/boxscores'):
    """
    Cargar todos los boxscores de ESPN para obtener game_ids y team names
    
    Returns:
        list of dicts con game_id, away_team, home_team
    """
    games = []
    
    boxscore_files = list(Path(boxscores_dir).glob('*.json'))
    
    logger.info(f"Cargando {len(boxscore_files)} boxscores de ESPN...")
    
    for file_path in boxscore_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extraer game_id del nombre del archivo
            espn_game_id = file_path.stem
            
            # Extraer team names - formato ESPN directo
            away_team = data.get('away_team', '')
            home_team = data.get('home_team', '')
            
            if away_team and home_team:
                games.append({
                    'espn_game_id': espn_game_id,
                    'away_team': away_team,
                    'home_team': home_team
                })
        except Exception as e:
            logger.warning(f"Error leyendo {file_path.name}: {e}")
            continue
    
    logger.success(f"✅ Cargados {len(games)} partidos")
    return games

def scrape_all_player_boxscores(
    games,
    output_dir='data/raw/nba_com_players',
    delay_seconds=1.0,
    resume=True
):
    """
    Scrapear player boxscores para todos los partidos
    
    Args:
        games: Lista de dicts con game_id, away_team, home_team
        output_dir: Directorio de salida
        delay_seconds: Delay entre requests (rate limiting)
        resume: Si True, skip partidos ya scrapeados
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Determinar cuáles ya están scrapeados
    existing_files = set(f.stem for f in Path(output_dir).glob('*.json'))
    
    if resume:
        games_to_scrape = [g for g in games if g['espn_game_id'] not in existing_files]
        logger.info(f"Modo resume: {len(existing_files)} ya scrapeados, {len(games_to_scrape)} pendientes")
    else:
        games_to_scrape = games
        logger.info(f"Scrapeando todos los {len(games_to_scrape)} partidos")
    
    # Stats
    successful = 0
    failed = 0
    failed_games = []
    
    # Progress bar
    pbar = tqdm(games_to_scrape, desc="Scrapeando player boxscores")
    
    for game in pbar:
        espn_game_id = game['espn_game_id']
        away_team = game['away_team']
        home_team = game['home_team']
        
        # Obtener slugs
        away_slug = get_team_slug(away_team)
        home_slug = get_team_slug(home_team)
        
        # Actualizar progress bar
        pbar.set_description(f"{away_slug.upper()} @ {home_slug.upper()}")
        
        try:
            # Scrapear
            result = scrape_player_boxscore(
                nba_com_game_id=espn_game_id,
                away_slug=away_slug,
                home_slug=home_slug
            )
            
            if result:
                save_player_boxscore(result, output_dir=output_dir)
                successful += 1
            else:
                failed += 1
                failed_games.append({
                    'game_id': espn_game_id,
                    'teams': f"{away_team} @ {home_team}"
                })
            
            # Rate limiting
            time.sleep(delay_seconds)
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Scraping interrumpido por usuario")
            break
        except Exception as e:
            logger.error(f"Error inesperado en {espn_game_id}: {e}")
            failed += 1
            failed_games.append({
                'game_id': espn_game_id,
                'teams': f"{away_team} @ {home_team}",
                'error': str(e)
            })
            continue
    
    # Resumen final
    print(f"\n{'='*80}")
    print(f"RESUMEN DE SCRAPING")
    print(f"{'='*80}")
    print(f"✅ Exitosos: {successful}")
    print(f"❌ Fallidos: {failed}")
    print(f"📊 Total procesados: {successful + failed}")
    print(f"📁 Guardados en: {output_dir}")
    
    if failed_games:
        print(f"\n⚠️  Partidos fallidos:")
        for game in failed_games[:10]:  # Mostrar primeros 10
            print(f"  - {game['game_id']}: {game['teams']}")
        if len(failed_games) > 10:
            print(f"  ... y {len(failed_games) - 10} más")
        
        # Guardar lista de fallidos
        with open('failed_nba_com_scrapes.json', 'w') as f:
            json.dump(failed_games, f, indent=2)
        print(f"\n💾 Lista completa guardada en: failed_nba_com_scrapes.json")

if __name__ == '__main__':
    # Cargar partidos de ESPN
    games = load_espn_boxscores()
    
    if not games:
        logger.error("❌ No se encontraron partidos para scrapear")
        exit(1)
    
    # Confirmar
    print(f"\n{'='*80}")
    print(f"Se scrapearán player boxscores para {len(games)} partidos")
    print(f"Delay entre requests: 1 segundo")
    print(f"Tiempo estimado: ~{len(games) / 60:.1f} minutos")
    print(f"{'='*80}\n")
    
    response = input("¿Continuar? (y/n): ")
    
    if response.lower() == 'y':
        scrape_all_player_boxscores(games, delay_seconds=1.0, resume=True)
    else:
        print("Scraping cancelado")
