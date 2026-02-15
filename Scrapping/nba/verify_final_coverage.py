"""
Verificación FINAL de cobertura post-scraping
"""

import json
import glob
from collections import Counter

def final_audit():
    # 1. Contar archivos JSON scrapeados
    files = glob.glob('data/raw/nba_com_players/*.json')
    total_scraped = len(files)
    
    print(f"📊 Total Player Boxscores Scrapeados: {total_scraped}")
    
    # 2. Cargar mapping para ver expectativas
    try:
        with open('data/espn_to_nba_mapping.json', 'r') as f:
            mapping = json.load(f)
        total_matched = len(mapping)
        print(f"🔗 Total Matched Games en Mapping: {total_matched}")
        
        # Diferencia
        pending = total_matched - total_scraped
        print(f"⏳ Pendientes de scrape: {pending}")
        
    except:
        print("❌ No se encontró mapping file")

    # 3. Datos de ESPN Totales
    espn_files = glob.glob('data/raw/boxscores/*.json')
    total_espn = len(espn_files)
    print(f"📁 Total ESPN Games Originales: {total_espn}")

    # 4. Cálculo de Cobertura
    if total_espn > 0:
        coverage = (total_matched / total_espn) * 100
        print(f"\n📈 COBERTURA DE MATCHING: {coverage:.1f}% ({total_matched}/{total_espn})")
    
    # 5. Muestra de juegos scrapeados (validar contenido)
    print("\n🔍 Validando muestra de 5 archivos recientes...")
    for fpath in files[-5:]:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            players = len(data.get('home_team', {}).get('players', [])) + \
                      len(data.get('away_team', {}).get('players', []))
            
            print(f"  - {fpath.split('\\')[-1]}: {players} jugadores extraídos ✅")
        except:
            print(f"  - {fpath}: Error leyendo archivo ❌")

if __name__ == '__main__':
    final_audit()
