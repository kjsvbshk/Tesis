"""
Auditar la posibilidad de cruzar games (ESPN) con nba_player_boxscores (NBA)
usando el archivo de mapping existente.
"""
import json
import psycopg2
from load_data import Config
from pathlib import Path

def audit_mapping():
    print("🕵️ Iniciando auditoría de cruce de datos...\n")
    
    # 1. Cargar Mapping
    mapping_path = Path('data/espn_to_nba_mapping.json')
    if not mapping_path.exists():
        print("❌ CRÍTICO: No se encontró data/espn_to_nba_mapping.json")
        return
        
    with open(mapping_path, 'r') as f:
        # espn_id -> nba_id
        mapping = json.load(f)
    print(f"📄 Mapping cargado: {len(mapping)} pares (ESPN -> NBA)")
    
    # Invertir mapping para búsqueda inversa
    nba_to_espn = {v: k for k, v in mapping.items()}
    
    # 2. Conectar a DB
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()
    
    # 3. Obtener IDs de tablas
    print("\n📊 Consultando base de datos...")
    
    # Games (ESPN)
    cur.execute("SELECT game_id FROM espn.games")
    games_ids = set(str(r[0]) for r in cur.fetchall())
    print(f"  - Tabla 'games' (ESPN IDs): {len(games_ids)}")
    
    # NBA Player Boxscores (NBA)
    cur.execute("SELECT DISTINCT game_id FROM espn.nba_player_boxscores")
    nba_box_ids = set(str(r[0]) for r in cur.fetchall())
    print(f"  - Tabla 'nba_player_boxscores' (NBA IDs): {len(nba_box_ids)}")
    
    conn.close()
    
    # 4. Análisis de Cobertura
    print("\n🔍 Análisis de Cruce:")
    
    # A. Games en DB que tienen Mapping
    games_with_mapping = [gid for gid in games_ids if gid in mapping]
    coverage_games = len(games_with_mapping) / len(games_ids) * 100 if games_ids else 0
    
    print(f"  A. Games en DB con Mapping a NBA ID: {len(games_with_mapping)} / {len(games_ids)} ({coverage_games:.1f}%)")
    
    missing_games = list(games_ids - set(mapping.keys()))
    if missing_games:
        print(f"     ⚠️  Faltan {len(missing_games)} juegos en el mapping (ej: {missing_games[:3]})")
    
    # B. Games en DB que tienen datos de jugadores (vía mapping)
    games_with_player_data = []
    for gid in games_with_mapping:
        nba_id = mapping[gid]
        if nba_id in nba_box_ids:
            games_with_player_data.append(gid)
            
    coverage_data = len(games_with_player_data) / len(games_ids) * 100 if games_ids else 0
    print(f"  B. Games en DB con DATOS DE JUGADORES linkeables: {len(games_with_player_data)} / {len(games_ids)} ({coverage_data:.1f}%)")
    
    # C. Análisis de 'nba_player_boxscores' huérfanos?
    # IDs en nba_player_boxscores que no mapean a ningun juego en 'games'
    orphaned_nba_data = []
    for nba_id in nba_box_ids:
        espn_id = nba_to_espn.get(nba_id)
        if not espn_id or espn_id not in games_ids:
            orphaned_nba_data.append(nba_id)
            
    print(f"  C. Boxscores NBA que no cruzan con tabla 'games': {len(orphaned_nba_data)} / {len(nba_box_ids)}")
    print("     (Esto es normal si scrapeamos más temporadas de las que hay en 'games')")

    # Recomendación
    print("\n💡 CONCLUSIÓN Y RECOMENDACIÓN:")
    if coverage_data < 80:
        print("  ⚠️  El cruce es bajo. La tabla 'games' parece tener datos viejos o incompletos comparado con el nuevo scraping.")
        print("  ❌ NO crear vistas todavía sin actualizar 'games'.")
    else:
        print("  ✅ El cruce es sólido.")
        print("  ✅ RECOMENDACIÓN: Cargar el mapping en una tabla 'espn_nba_mapping' para habilitar JOINs.")

if __name__ == '__main__':
    audit_mapping()
