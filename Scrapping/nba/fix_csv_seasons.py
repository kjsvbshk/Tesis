import pandas as pd
from pathlib import Path
import os

def fix_standings_seasons():
    base_dir = Path('data/raw/standings')
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return

    csv_files = list(base_dir.glob('*.csv'))
    print(f"Found {len(csv_files)} files in {base_dir}")

    for file_path in csv_files:
        try:
            # Expected filename format: "2023-24.csv"
            filename = file_path.stem # "2023-24"
            
            # Simple validation: contains hyphen
            if '-' not in filename:
                print(f"Skipping {filename} (unexpected format)")
                continue
                
            df = pd.read_csv(file_path)
            
            # Check if season column exists and is wrong
            if 'season' in df.columns:
                # Update season column with filename value
                df['season'] = filename
                
                # Save back to CSV
                df.to_csv(file_path, index=False)
                print(f"✅ Fixed {file_path.name}: season -> {filename}")
            else:
                print(f"⚠️ {file_path.name} missing 'season' column")
                
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")

if __name__ == '__main__':
    fix_standings_seasons()
