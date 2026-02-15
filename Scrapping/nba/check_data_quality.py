import os
import json

boxscores_dir = "data/raw/boxscores"
files = [f for f in os.listdir(boxscores_dir) if f.endswith('.json')]

print(f"Total boxscores: {len(files)}")

valid_teams = 0
valid_scores = 0
with_stats = 0
sample_files = []

for i, filename in enumerate(files[:100]):
    filepath = os.path.join(boxscores_dir, filename)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        has_teams = data.get('home_team') and data.get('away_team')
        has_scores = data.get('home_score') is not None and data.get('away_score') is not None
        has_stats = bool(data.get('home_stats')) and bool(data.get('away_stats'))
        
        if has_teams:
            valid_teams += 1
        if has_scores:
            valid_scores += 1
        if has_stats:
            with_stats += 1
            
        if i < 3:
            sample_files.append({
                'file': filename,
                'teams': has_teams,
                'scores': has_scores,
                'stats': has_stats,
                'data': data
            })
    except Exception as e:
        print(f"Error reading {filename}: {e}")

print(f"\nMuestra de 100 archivos:")
print(f"Con teams válidos: {valid_teams}/100")
print(f"Con scores válidos: {valid_scores}/100")
print(f"Con stats: {with_stats}/100")

print(f"\nMuestra de primeros 3 archivos:")
for sample in sample_files:
    print(f"\n{sample['file']}:")
    print(f"  Teams: {sample['teams']}, Scores: {sample['scores']}, Stats: {sample['stats']}")
    if sample['data']:
        print(f"  {sample['data'].get('away_team')} {sample['data'].get('away_score')} @ {sample['data'].get('home_team')} {sample['data'].get('home_score')}")
