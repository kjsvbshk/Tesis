import os
import json
from collections import defaultdict

boxscores_dir = "data/raw/boxscores"
files = [f for f in os.listdir(boxscores_dir) if f.endswith('.json')]

print(f"{'='*80}")
print(f"VERIFICACIÓN COMPLETA DE SCRAPING")
print(f"{'='*80}\n")

print(f"📊 TOTAL BOXSCORES: {len(files)}\n")

# Validate data quality
valid_teams = 0
valid_scores = 0
complete_stats = 0
empty_stats = 0
partial_stats = 0

required_stats = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'FG%', '3P%', 'FT%']

# Sample validation
sample_size = min(100, len(files))
for filename in files[:sample_size]:
    filepath = os.path.join(boxscores_dir, filename)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Check teams
        if data.get('home_team') and data.get('away_team'):
            valid_teams += 1
        
        # Check scores
        if data.get('home_score') is not None and data.get('away_score') is not None:
            valid_scores += 1
        
        # Check stats
        home_stats = data.get('home_stats', {})
        away_stats = data.get('away_stats', {})
        
        home_complete = sum(1 for stat in required_stats if home_stats.get(stat) is not None)
        away_complete = sum(1 for stat in required_stats if away_stats.get(stat) is not None)
        
        if home_complete == 10 and away_complete == 10:
            complete_stats += 1
        elif home_complete == 0 and away_complete == 0:
            empty_stats += 1
        else:
            partial_stats += 1
            
    except Exception as e:
        print(f"Error reading {filename}: {e}")

print(f"🔍 VALIDACIÓN (muestra de {sample_size} archivos):")
print(f"  ✅ Con teams válidos: {valid_teams}/{sample_size} ({valid_teams/sample_size*100:.1f}%)")
print(f"  ✅ Con scores válidos: {valid_scores}/{sample_size} ({valid_scores/sample_size*100:.1f}%)")
print(f"  ✅ Stats completos (10/10): {complete_stats}/{sample_size} ({complete_stats/sample_size*100:.1f}%)")
print(f"  ⚠️  Stats vacíos (0/10): {empty_stats}/{sample_size} ({empty_stats/sample_size*100:.1f}%)")
print(f"  ⚠️  Stats parciales: {partial_stats}/{sample_size} ({partial_stats/sample_size*100:.1f}%)")

# Show sample of complete data
print(f"\n📋 MUESTRA DE DATOS COMPLETOS:")
for filename in files[:3]:
    filepath = os.path.join(boxscores_dir, filename)
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    print(f"\n  {filename}:")
    print(f"    {data.get('away_team')} {data.get('away_score')} @ {data.get('home_team')} {data.get('home_score')}")
    home_stats = data.get('home_stats', {})
    if home_stats:
        print(f"    Home: PTS={home_stats.get('PTS')}, REB={home_stats.get('REB')}, AST={home_stats.get('AST')}, FG%={home_stats.get('FG%')}")

# Estimate total based on sample
if sample_size > 0:
    estimated_complete = int((complete_stats / sample_size) * len(files))
    estimated_empty = int((empty_stats / sample_size) * len(files))
    
    print(f"\n📈 ESTIMACIÓN TOTAL:")
    print(f"  Boxscores completos: ~{estimated_complete}/{len(files)}")
    print(f"  Boxscores vacíos: ~{estimated_empty}/{len(files)}")

print(f"\n{'='*80}")
if complete_stats == sample_size:
    print("✅ CALIDAD: EXCELENTE - Todos los datos completos")
elif complete_stats >= sample_size * 0.9:
    print("✅ CALIDAD: BUENA - >90% datos completos")
elif complete_stats >= sample_size * 0.5:
    print("⚠️  CALIDAD: ACEPTABLE - >50% datos completos")
else:
    print("❌ CALIDAD: INSUFICIENTE - <50% datos completos")
print(f"{'='*80}")
