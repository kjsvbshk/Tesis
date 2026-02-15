"""
Analizar por qué fallaron los matches de ESPN
"""

import json
import os
from collections import Counter

def analyze_unmatched():
    # Cargar mapping y unmatched
    try:
        with open('data/espn_to_nba_mapping.json', 'r') as f:
            mapping = json.load(f)
        print(f"✅ Matched games: {len(mapping)}")
    except:
        print("No mapping file found")
        mapping = {}

    # Cargar unmatched
    try:
        with open('data/unmatched_espn_games.json', 'r') as f:
            unmatched_ids = json.load(f)
        print(f"❌ Unmatched games: {len(unmatched_ids)}")
    except:
        print("No unmatched file found")
        return

    # Analizar causas
    corrupted_count = 0
    valid_but_unmatched_count = 0
    
    unmatched_samples = []

    print("\nAnalizando causa de fallo para unmatched games...")
    
    for espn_id in unmatched_ids:
        file_path = f"data/raw/boxscores/{espn_id}.json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            home = data.get('home_team')
            away = data.get('away_team')
            home_score = data.get('home_score')
            away_score = data.get('away_score')
            
            if not home or not away:
                corrupted_count += 1
            else:
                valid_but_unmatched_count += 1
                if len(unmatched_samples) < 20:
                    unmatched_samples.append({
                        'id': espn_id,
                        'matchup': f"{away} @ {home}",
                        'score': f"{away_score} - {home_score}",
                        'date': data.get('fecha')
                    })
                    
        except Exception:
            print(f"Error leyendo {file_path}")

    print(f"\nResultados del análisis:")
    print(f"💀 Archivos corruptos (None/None): {corrupted_count}")
    print(f"🤔 Archivos válidos sin match: {valid_but_unmatched_count}")
    
    if valid_but_unmatched_count > 0:
        print(f"\nEjemplos de válidos sin match (Top 20):")
        for sample in unmatched_samples:
            print(f"  ID: {sample['id']} | {sample['matchup']} | Score: {sample['score']} | Date: {sample['date']}")

if __name__ == '__main__':
    analyze_unmatched()
