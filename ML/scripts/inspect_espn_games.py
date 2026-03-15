from sqlalchemy import create_engine, text
import sys
from pathlib import Path
import pandas as pd

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def inspect_espn_games():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- Checking espn.games columns ---")
        
        cols_to_check = [
            'home_fg_pct', 'home_reb', 'home_ast', 'home_to', 'home_pts',
            'away_fg_pct', 'away_reb', 'away_ast', 'away_to', 'away_pts',
            'point_diff', 'reb_diff', 'ast_diff'
        ]
        
        try:
            total = conn.execute(text("SELECT COUNT(*) FROM espn.games")).scalar()
            print(f"Total Rows: {total}")
            
            for col in cols_to_check:
                try:
                    # Check if col exists first (to avoid error if schema implies it but it's not there)
                    # Actually standard check
                    nulls = conn.execute(text(f"SELECT COUNT(*) FROM espn.games WHERE {col} IS NULL")).scalar()
                    print(f"{col:<15}: {nulls} nulls ({nulls/total*100:.1f}%)")
                    
                    if nulls < total:
                         sample = conn.execute(text(f"SELECT {col} FROM espn.games WHERE {col} IS NOT NULL LIMIT 3")).fetchall()
                         print(f"   Sample: {[r[0] for r in sample]}")
                         
                except Exception as e:
                    print(f"{col:<15}: Error (maybe col missing): {e}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    inspect_espn_games()
