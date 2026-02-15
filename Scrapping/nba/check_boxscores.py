import json
import os

boxscores_dir = "data/raw/boxscores"
files = [f for f in os.listdir(boxscores_dir) if f.endswith('.json')]

valid_count = 0
empty_count = 0
sample_valid = []
sample_empty = []

for i, filename in enumerate(files[:100]):  # Check first 100
    filepath = os.path.join(boxscores_dir, filename)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        if data.get('home_team') and data.get('away_team'):
            valid_count += 1
            if len(sample_valid) < 3:
                sample_valid.append((filename, data.get('home_team'), data.get('away_team'), data.get('fecha')))
        else:
            empty_count += 1
            if len(sample_empty) < 3:
                sample_empty.append((filename, data.get('fecha')))
    except Exception as e:
        print(f"Error reading {filename}: {e}")

print(f"Sample of 100 files:")
print(f"Valid: {valid_count}")
print(f"Empty: {empty_count}")
print(f"\nValid samples:")
for f, home, away, date in sample_valid:
    print(f"  {f}: {home} vs {away} on {date}")
print(f"\nEmpty samples:")
for f, date in sample_empty:
    print(f"  {f}: fecha={date}, teams=NULL")
