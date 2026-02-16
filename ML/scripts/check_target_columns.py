from sqlalchemy import create_engine, text
import sys
from pathlib import Path
import pandas as pd

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def check_targets():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- Checking Target Columns in ml.ml_ready_games ---")
        
        # Check null/zero counts for specific columns
        cols = ['home_to', 'away_to', 'home_pts', 'away_pts', 'point_diff', 'net_rating_diff', 'home_injuries_count', 'injuries_diff']
        
        for col in cols:
            try:
                nulls = conn.execute(text(f"SELECT COUNT(*) FROM ml.ml_ready_games WHERE {col} IS NULL")).scalar()
                zeros = conn.execute(text(f"SELECT COUNT(*) FROM ml.ml_ready_games WHERE {col} = 0")).scalar()
                total = conn.execute(text(f"SELECT COUNT(*) FROM ml.ml_ready_games")).scalar()
                
                print(f"{col:<15} | Total: {total:<5} | Nulls: {nulls:<5} ({nulls/total*100:.1f}%) | Zeros: {zeros:<5} ({zeros/total*100:.1f}%)")
                
                # Sample values if not all null
                if total - nulls > 0:
                    sample = conn.execute(text(f"SELECT {col} FROM ml.ml_ready_games WHERE {col} IS NOT NULL LIMIT 3")).fetchall()
                    print(f"   Sample: {[r[0] for r in sample]}")
            except Exception as e:
                print(f"{col:<15} | Error: {e}")

        print("\n--- Checking Boxscore Source for Turnovers ---")
        try:
            # Check if we have 'to_stat' or 'tov' in boxscores
            # I suspect the column name might be 'to_stat' based on previous inspection
            tov_sample = conn.execute(text("SELECT to_stat FROM espn.nba_player_boxscores WHERE to_stat > 0 LIMIT 5")).fetchall()
            print(f"Sample non-zero 'to_stat' from nba_player_boxscores: {[r[0] for r in tov_sample]}")
        except Exception as e:
            print(f"Error checking boxscores: {e}")

if __name__ == "__main__":
    check_targets()
