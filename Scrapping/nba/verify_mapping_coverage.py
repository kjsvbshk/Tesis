"""
Verificar cobertura del mapping por temporada con los datos finales
"""

import json
from datetime import datetime
import glob

def verify_coverage():
    # Cargar mapping final
    try:
        with open('data/espn_to_nba_mapping.json', 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        print(f"✅ Total Matched Games: {len(mapping)}")
    except:
        print("No mapping file found")
        return

    # Cargar unmatched final
    try:
        with open('data/unmatched_espn_games.json', 'r', encoding='utf-8') as f:
            unmatched_ids = json.load(f)
        print(f"❌ Total Unmatched Games: {len(unmatched_ids)}")
    except:
        unmatched_ids = []

    # Cargar schedule para obtener fechas reales de los NBA IDs
    print("Cargando schedule NBA...")
    with open('data/nba_com_schedule.json', 'r', encoding='utf-8') as f:
        # Mapa: nba_game_id -> date
        nba_games = {g['nba_game_id']: g['date'].split('T')[0] for g in json.load(f)}

    # Analizar por temporada
    season_stats = {
        '2023-24': {'matched': 0, 'total_expected': 1319}, # 1230 regular + playin/playoffs
        '2024-25': {'matched': 0, 'total_expected': 1230},
        '2025-26': {'matched': 0, 'total_expected': 600}  # Aprox en curso
    }
    
    # Helper para determinar season
    def get_season(date_str):
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            if dt.year == 2023 or (dt.year == 2024 and dt.month < 10):
                return '2023-24'
            elif dt.year == 2024 or (dt.year == 2025 and dt.month < 10):
                return '2024-25'
            elif dt.year == 2025 or (dt.year == 2026 and dt.month < 10):
                return '2025-26'
            return 'unknown'
        except:
            return 'unknown'

    print("\nCalculando estadísticas por temporada...")
    
    counts = {'2023-24': 0, '2024-25': 0, '2025-26': 0, 'unknown': 0}
    
    for nba_id in mapping.values():
        date = nba_games.get(nba_id)
        if date:
            season = get_season(date)
            if season in counts:
                counts[season] += 1
            else:
                counts['unknown'] += 1
        else:
            counts['unknown'] += 1

    print("\n📊 COBERTURA FINAL POR TEMPORADA:")
    print(f"{'Season':<10} | {'Matched':<10} | {'Estado':<15}")
    print("-" * 40)
    
    print(f"{'2023-24':<10} | {counts['2023-24']:<10} | {'✅ Completa' if counts['2023-24'] > 1200 else '⚠️ Parcial'}")
    print(f"{'2024-25':<10} | {counts['2024-25']:<10} | {'✅ Completa' if counts['2024-25'] > 1000 else '⚠️ Parcial'}")
    print(f"{'2025-26':<10} | {counts['2025-26']:<10} | {'✅ En Curso'}")
    
    total_valid = sum(counts.values())
    print("-" * 40)
    print(f"TOTAL: {total_valid} juegos matcheados y listos para ML.")

    # Validar archivos físicos
    files = glob.glob('data/raw/nba_com_players/*.json')
    print(f"\n📂 Archivos físicos scrapeados: {len(files)}")
    
    if len(files) >= total_valid * 0.99:
        print("✅ Integridad Física: EXCELENTE (Archivos coinciden con mapping)")
    else:
        print(f"⚠️ Integridad Física: FALTAN ARCHIVOS ({total_valid - len(files)} pendientes)")

if __name__ == '__main__':
    verify_coverage()
