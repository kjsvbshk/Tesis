#!/usr/bin/env python3
"""
Script para cargar equipos y estadísticas de equipos por juego desde datos del scrapping
a las tablas espn.teams y espn.team_stats_game
"""

import os
import sys
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import json

# Agregar el directorio Backend al path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import get_espn_db
from app.models.team import Team
from app.models.team_stats import TeamStatsGame
from app.models.game import Game
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect

# Mapeo completo de equipos NBA con información completa
TEAM_INFO = {
    'atl': {'name': 'Atlanta Hawks', 'city': 'Atlanta', 'conference': 'Eastern', 'division': 'Southeast'},
    'bkn': {'name': 'Brooklyn Nets', 'city': 'Brooklyn', 'conference': 'Eastern', 'division': 'Atlantic'},
    'bos': {'name': 'Boston Celtics', 'city': 'Boston', 'conference': 'Eastern', 'division': 'Atlantic'},
    'cha': {'name': 'Charlotte Hornets', 'city': 'Charlotte', 'conference': 'Eastern', 'division': 'Southeast'},
    'chi': {'name': 'Chicago Bulls', 'city': 'Chicago', 'conference': 'Eastern', 'division': 'Central'},
    'cle': {'name': 'Cleveland Cavaliers', 'city': 'Cleveland', 'conference': 'Eastern', 'division': 'Central'},
    'dal': {'name': 'Dallas Mavericks', 'city': 'Dallas', 'conference': 'Western', 'division': 'Southwest'},
    'den': {'name': 'Denver Nuggets', 'city': 'Denver', 'conference': 'Western', 'division': 'Northwest'},
    'det': {'name': 'Detroit Pistons', 'city': 'Detroit', 'conference': 'Eastern', 'division': 'Central'},
    'gs': {'name': 'Golden State Warriors', 'city': 'San Francisco', 'conference': 'Western', 'division': 'Pacific'},
    'hou': {'name': 'Houston Rockets', 'city': 'Houston', 'conference': 'Western', 'division': 'Southwest'},
    'ind': {'name': 'Indiana Pacers', 'city': 'Indianapolis', 'conference': 'Eastern', 'division': 'Central'},
    'lac': {'name': 'LA Clippers', 'city': 'Los Angeles', 'conference': 'Western', 'division': 'Pacific'},
    'lal': {'name': 'Los Angeles Lakers', 'city': 'Los Angeles', 'conference': 'Western', 'division': 'Pacific'},
    'mem': {'name': 'Memphis Grizzlies', 'city': 'Memphis', 'conference': 'Western', 'division': 'Southwest'},
    'mia': {'name': 'Miami Heat', 'city': 'Miami', 'conference': 'Eastern', 'division': 'Southeast'},
    'mil': {'name': 'Milwaukee Bucks', 'city': 'Milwaukee', 'conference': 'Eastern', 'division': 'Central'},
    'min': {'name': 'Minnesota Timberwolves', 'city': 'Minneapolis', 'conference': 'Western', 'division': 'Northwest'},
    'no': {'name': 'New Orleans Pelicans', 'city': 'New Orleans', 'conference': 'Western', 'division': 'Southwest'},
    'ny': {'name': 'New York Knicks', 'city': 'New York', 'conference': 'Eastern', 'division': 'Atlantic'},
    'okc': {'name': 'Oklahoma City Thunder', 'city': 'Oklahoma City', 'conference': 'Western', 'division': 'Northwest'},
    'orl': {'name': 'Orlando Magic', 'city': 'Orlando', 'conference': 'Eastern', 'division': 'Southeast'},
    'phi': {'name': 'Philadelphia 76ers', 'city': 'Philadelphia', 'conference': 'Eastern', 'division': 'Atlantic'},
    'phx': {'name': 'Phoenix Suns', 'city': 'Phoenix', 'conference': 'Western', 'division': 'Pacific'},
    'por': {'name': 'Portland Trail Blazers', 'city': 'Portland', 'conference': 'Western', 'division': 'Northwest'},
    'sa': {'name': 'San Antonio Spurs', 'city': 'San Antonio', 'conference': 'Western', 'division': 'Southwest'},
    'sac': {'name': 'Sacramento Kings', 'city': 'Sacramento', 'conference': 'Western', 'division': 'Pacific'},
    'tor': {'name': 'Toronto Raptors', 'city': 'Toronto', 'conference': 'Eastern', 'division': 'Atlantic'},
    'utah': {'name': 'Utah Jazz', 'city': 'Salt Lake City', 'conference': 'Western', 'division': 'Northwest'},
    'wsh': {'name': 'Washington Wizards', 'city': 'Washington', 'conference': 'Eastern', 'division': 'Southeast'},
}

# Mapeo de nombres alternativos a abreviaciones
NAME_TO_ABBREV = {
    'Atlanta Hawks': 'atl', 'Hawks': 'atl',
    'Brooklyn Nets': 'bkn', 'Nets': 'bkn',
    'Boston Celtics': 'bos', 'Celtics': 'bos',
    'Charlotte Hornets': 'cha', 'Hornets': 'cha',
    'Chicago Bulls': 'chi', 'Bulls': 'chi',
    'Cleveland Cavaliers': 'cle', 'Cavaliers': 'cle',
    'Dallas Mavericks': 'dal', 'Mavericks': 'dal',
    'Denver Nuggets': 'den', 'Nuggets': 'den',
    'Detroit Pistons': 'det', 'Pistons': 'det',
    'Golden State Warriors': 'gs', 'Warriors': 'gs',
    'Houston Rockets': 'hou', 'Rockets': 'hou',
    'Indiana Pacers': 'ind', 'Pacers': 'ind',
    'LA Clippers': 'lac', 'La Clippers': 'lac', 'Clippers': 'lac',
    'Los Angeles Lakers': 'lal', 'Lakers': 'lal',
    'Memphis Grizzlies': 'mem', 'Grizzlies': 'mem',
    'Miami Heat': 'mia', 'Heat': 'mia',
    'Milwaukee Bucks': 'mil', 'Bucks': 'mil',
    'Minnesota Timberwolves': 'min', 'Timberwolves': 'min',
    'New Orleans Pelicans': 'no', 'Pelicans': 'no',
    'New York Knicks': 'ny', 'Knicks': 'ny',
    'Oklahoma City Thunder': 'okc', 'Thunder': 'okc',
    'Orlando Magic': 'orl', 'Magic': 'orl',
    'Philadelphia 76ers': 'phi', '76ers': 'phi', 'Philadelphia 76Ers': 'phi',
    'Phoenix Suns': 'phx', 'Suns': 'phx',
    'Portland Trail Blazers': 'por', 'Trail Blazers': 'por',
    'San Antonio Spurs': 'sa', 'Spurs': 'sa',
    'Sacramento Kings': 'sac', 'Kings': 'sac',
    'Toronto Raptors': 'tor', 'Raptors': 'tor',
    'Utah Jazz': 'utah', 'Jazz': 'utah',
    'Washington Wizards': 'wsh', 'Wizards': 'wsh',
}

def normalize_abbrev(abbrev: str) -> str:
    """Normalizar abreviación a minúsculas"""
    if not abbrev:
        return None
    return abbrev.lower().strip()

def get_team_abbrev_from_name(name: str) -> Optional[str]:
    """Obtener abreviación desde nombre del equipo"""
    if not name:
        return None
    name = name.strip()
    # Intentar mapeo directo
    if name in NAME_TO_ABBREV:
        return NAME_TO_ABBREV[name]
    # Intentar con minúsculas
    if name.lower() in NAME_TO_ABBREV:
        return NAME_TO_ABBREV[name.lower()]
    return None

def load_teams(db: Session) -> Dict[str, int]:
    """
    Cargar equipos a la tabla espn.teams desde los datos del scrapping
    Retorna un diccionario de abreviación -> team_id
    """
    print("Cargando equipos...")
    
    # Obtener equipos únicos desde team_stats CSV
    scrapping_dir = Path(__file__).parent.parent / 'Scrapping' / 'nba' / 'data' / 'raw'
    team_stats_dir = scrapping_dir / 'team_stats'
    
    teams_data = {}
    
    # Leer desde team_stats CSV files
    if team_stats_dir.exists():
        for season_dir in team_stats_dir.iterdir():
            if not season_dir.is_dir():
                continue
            for category_dir in ['offensive', 'defensive']:
                csv_file = season_dir / category_dir / 'all_teams.csv'
                if csv_file.exists():
                    try:
                        df = pd.read_csv(csv_file)
                        for _, row in df.iterrows():
                            team_name = row.get('team_name', '').strip()
                            team_abbrev = normalize_abbrev(row.get('team_abbrev', ''))
                            
                            if not team_name or not team_abbrev:
                                continue
                            
                            # Si no tenemos info completa, usar el mapeo
                            if team_abbrev not in teams_data:
                                if team_abbrev in TEAM_INFO:
                                    teams_data[team_abbrev] = {
                                        'name': TEAM_INFO[team_abbrev]['name'],
                                        'abbreviation': team_abbrev.upper(),
                                        'city': TEAM_INFO[team_abbrev]['city'],
                                        'conference': TEAM_INFO[team_abbrev]['conference'],
                                        'division': TEAM_INFO[team_abbrev]['division'],
                                    }
                                else:
                                    # Intentar obtener desde el nombre
                                    abbrev_from_name = get_team_abbrev_from_name(team_name)
                                    if abbrev_from_name and abbrev_from_name in TEAM_INFO:
                                        teams_data[abbrev_from_name] = {
                                            'name': TEAM_INFO[abbrev_from_name]['name'],
                                            'abbreviation': abbrev_from_name.upper(),
                                            'city': TEAM_INFO[abbrev_from_name]['city'],
                                            'conference': TEAM_INFO[abbrev_from_name]['conference'],
                                            'division': TEAM_INFO[abbrev_from_name]['division'],
                                        }
                    except Exception as e:
                        print(f"[WARN] Error leyendo {csv_file}: {e}")
                        continue
    
    # También leer desde standings si existe
    standings_file = scrapping_dir / 'standings_2024.csv'
    if standings_file.exists():
        try:
            df = pd.read_csv(standings_file)
            for _, row in df.iterrows():
                team_name = row.get('team_name', '').strip()
                team_abbrev = normalize_abbrev(row.get('team_abbrev', ''))
                conference = row.get('conference', '').strip()
                
                if not team_name:
                    continue
                
                # Normalizar conference
                if 'Eastern' in conference:
                    conference = 'Eastern'
                elif 'Western' in conference:
                    conference = 'Western'
                
                if not team_abbrev:
                    team_abbrev = get_team_abbrev_from_name(team_name)
                
                if team_abbrev and team_abbrev not in teams_data:
                    if team_abbrev in TEAM_INFO:
                        teams_data[team_abbrev] = {
                            'name': TEAM_INFO[team_abbrev]['name'],
                            'abbreviation': team_abbrev.upper(),
                            'city': TEAM_INFO[team_abbrev]['city'],
                            'conference': conference or TEAM_INFO[team_abbrev]['conference'],
                            'division': TEAM_INFO[team_abbrev]['division'],
                        }
        except Exception as e:
            print(f"[WARN] Error leyendo {standings_file}: {e}")
    
    # Si no encontramos equipos, usar el mapeo completo
    if not teams_data:
        print("[WARN] No se encontraron equipos en CSV, usando mapeo completo...")
        for abbrev, info in TEAM_INFO.items():
            teams_data[abbrev] = {
                'name': info['name'],
                'abbreviation': abbrev.upper(),
                'city': info['city'],
                'conference': info['conference'],
                'division': info['division'],
            }
    
    print(f"  {len(teams_data)} equipos encontrados")
    
    # Cargar a la base de datos
    team_id_map = {}
    next_team_id = 1
    
    for abbrev, team_info in teams_data.items():
        # Verificar si ya existe
        existing = db.query(Team).filter(
            Team.abbreviation == team_info['abbreviation']
        ).first()
        
        if existing:
            team_id_map[abbrev] = existing.team_id
            print(f"  [OK] {team_info['name']} ya existe (ID: {existing.team_id})")
        else:
            # Obtener el siguiente team_id disponible
            max_id = db.query(Team.team_id).order_by(Team.team_id.desc()).first()
            if max_id:
                next_team_id = max_id[0] + 1
            
            team = Team(
                team_id=next_team_id,
                name=team_info['name'],
                abbreviation=team_info['abbreviation'],
                city=team_info['city'],
                conference=team_info['conference'],
                division=team_info['division']
            )
            db.add(team)
            team_id_map[abbrev] = next_team_id
            print(f"  [NEW] {team_info['name']} creado (ID: {next_team_id})")
            next_team_id += 1
    
    db.commit()
    print(f"[OK] {len(team_id_map)} equipos cargados\n")
    return team_id_map

def load_team_stats_game_from_boxscores(db: Session, team_id_map: Dict[str, int]):
    """
    Cargar estadísticas de equipos por juego desde boxscores JSON
    """
    print("Cargando estadisticas de equipos por juego desde boxscores...")
    
    scrapping_dir = Path(__file__).parent.parent / 'Scrapping' / 'nba' / 'data' / 'raw'
    boxscores_dir = scrapping_dir / 'boxscores'
    
    if not boxscores_dir.exists():
        print("[WARN] Directorio de boxscores no existe")
        return
    
    json_files = list(boxscores_dir.glob('*.json'))
    if not json_files:
        print("[WARN] No se encontraron archivos JSON de boxscores")
        return
    
    print(f"  {len(json_files)} archivos de boxscores encontrados")
    
    loaded_count = 0
    skipped_count = 0
    error_count = 0
    batch_size = 100  # Hacer commit cada 100 registros
    
    for idx, json_file in enumerate(json_files, 1):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                boxscore = json.load(f)
            
            game_id = int(boxscore.get('game_id', 0))
            if not game_id:
                continue
            
            # Verificar si el juego existe usando SQL directo (evita problemas con columnas faltantes)
            result = db.execute(text("SELECT COUNT(*) FROM espn.games WHERE game_id = :game_id"), {"game_id": game_id})
            game_exists = result.scalar() > 0
            
            if not game_exists:
                skipped_count += 1
                continue
            
            home_team_name = boxscore.get('home_team', '').strip()
            away_team_name = boxscore.get('away_team', '').strip()
            
            # Obtener team_ids
            home_abbrev = get_team_abbrev_from_name(home_team_name)
            away_abbrev = get_team_abbrev_from_name(away_team_name)
            
            if not home_abbrev or home_abbrev not in team_id_map:
                continue
            if not away_abbrev or away_abbrev not in team_id_map:
                continue
            
            home_team_id = team_id_map[home_abbrev]
            away_team_id = team_id_map[away_abbrev]
            
            # Procesar estadísticas del equipo local
            home_stats = boxscore.get('home_stats', {})
            if home_stats:
                # Verificar si ya existe
                existing = db.query(TeamStatsGame).filter(
                    TeamStatsGame.game_id == game_id,
                    TeamStatsGame.team_id == home_team_id
                ).first()
                
                if not existing:
                    # Usar PTS de stats, o home_score como fallback
                    points = home_stats.get('PTS')
                    if points is None:
                        points = boxscore.get('home_score')
                    
                    team_stats = TeamStatsGame(
                        game_id=game_id,
                        team_id=home_team_id,
                        is_home=True,
                        points=int(points) if points is not None else None,
                        rebounds=int(home_stats.get('REB', 0)) if home_stats.get('REB') else None,
                        assists=int(home_stats.get('AST', 0)) if home_stats.get('AST') else None,
                        steals=int(home_stats.get('STL', 0)) if home_stats.get('STL') else None,
                        blocks=int(home_stats.get('BLK', 0)) if home_stats.get('BLK') else None,
                        turnovers=int(home_stats.get('TO', 0)) if home_stats.get('TO') else None,
                        personal_fouls=int(home_stats.get('PF', 0)) if home_stats.get('PF') else None,
                        field_goal_percentage=float(home_stats.get('FG%', 0)) if home_stats.get('FG%') else None,
                        three_point_percentage=float(home_stats.get('3P%', 0)) if home_stats.get('3P%') else None,
                        free_throw_percentage=float(home_stats.get('FT%', 0)) if home_stats.get('FT%') else None,
                    )
                    db.add(team_stats)
                    loaded_count += 1
            
            # Procesar estadísticas del equipo visitante
            away_stats = boxscore.get('away_stats', {})
            if away_stats:
                # Verificar si ya existe
                existing = db.query(TeamStatsGame).filter(
                    TeamStatsGame.game_id == game_id,
                    TeamStatsGame.team_id == away_team_id
                ).first()
                
                if not existing:
                    # Usar PTS de stats, o away_score como fallback
                    points = away_stats.get('PTS')
                    if points is None:
                        points = boxscore.get('away_score')
                    
                    team_stats = TeamStatsGame(
                        game_id=game_id,
                        team_id=away_team_id,
                        is_home=False,
                        points=int(points) if points is not None else None,
                        rebounds=int(away_stats.get('REB', 0)) if away_stats.get('REB') else None,
                        assists=int(away_stats.get('AST', 0)) if away_stats.get('AST') else None,
                        steals=int(away_stats.get('STL', 0)) if away_stats.get('STL') else None,
                        blocks=int(away_stats.get('BLK', 0)) if away_stats.get('BLK') else None,
                        turnovers=int(away_stats.get('TO', 0)) if away_stats.get('TO') else None,
                        personal_fouls=int(away_stats.get('PF', 0)) if away_stats.get('PF') else None,
                        field_goal_percentage=float(away_stats.get('FG%', 0)) if away_stats.get('FG%') else None,
                        three_point_percentage=float(away_stats.get('3P%', 0)) if away_stats.get('3P%') else None,
                        free_throw_percentage=float(away_stats.get('FT%', 0)) if away_stats.get('FT%') else None,
                    )
                    db.add(team_stats)
                    loaded_count += 1
            
            # Hacer commit periódicamente para evitar problemas de transacción
            if loaded_count > 0 and loaded_count % batch_size == 0:
                try:
                    db.commit()
                    print(f"  [PROGRESO] {loaded_count} registros procesados...")
                except Exception as e:
                    print(f"[WARN] Error en commit intermedio: {e}")
                    db.rollback()
            
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # Solo mostrar los primeros 10 errores
                print(f"[WARN] Error procesando {json_file.name}: {e}")
            elif error_count == 11:
                print(f"[WARN] ... (más errores, pero no se mostrarán)")
            db.rollback()  # Rollback en caso de error para continuar con el siguiente archivo
            continue
    
    # Commit final
    try:
        db.commit()
        print(f"[OK] {loaded_count} registros de estadisticas cargados")
        print(f"     {skipped_count} juegos sin match en BD")
        print(f"     {error_count} archivos con errores\n")
    except Exception as e:
        print(f"[ERROR] Error al hacer commit final: {e}")
        db.rollback()

def main():
    """Función principal"""
    print("=" * 80)
    print("CARGA DE EQUIPOS Y ESTADÍSTICAS DE EQUIPOS POR JUEGO")
    print("=" * 80)
    print()
    
    # Obtener sesión de base de datos
    db = next(get_espn_db())
    
    try:
        # Cargar equipos
        team_id_map = load_teams(db)
        
        # Cargar estadísticas de equipos por juego
        load_team_stats_game_from_boxscores(db, team_id_map)
        
        print("=" * 80)
        print("[OK] CARGA COMPLETADA")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

