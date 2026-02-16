from sqlalchemy import create_engine, text
import sys
from pathlib import Path
import pandas as pd

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def debug_mapping():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- Debugging Injury Mapping ---")
        
        # Get injury teams
        inj_teams = pd.read_sql("SELECT DISTINCT team FROM espn.injuries", conn)['team'].tolist()
        inj_teams.sort()
        print(f"Injuries Teams ({len(inj_teams)}): {inj_teams[:5]}...")
        
        # Get game teams
        game_teams = pd.read_sql("SELECT DISTINCT home_team FROM ml.ml_ready_games", conn)['home_team'].tolist()
        game_teams.sort()
        print(f"Games Teams ({len(game_teams)}): {game_teams[:5]}...")
        
        # Check intersection
        common = set(inj_teams).intersection(set(game_teams))
        print(f"Common Teams: {len(common)}")
        
        missing_in_inj = set(game_teams) - set(inj_teams)
        if missing_in_inj:
            print(f"Teams in Games but NOT in Injuries: {missing_in_inj}")
            
        # Check normalization (strip, lower)
        print("\n--- Normalization Check ---")
        inj_norm = {t.strip().lower(): t for t in inj_teams}
        game_norm = {t.strip().lower(): t for t in game_teams}
        
        common_norm = set(inj_norm.keys()).intersection(set(game_norm.keys()))
        print(f"Common Teams (Normalized): {len(common_norm)}")
        
        if len(common_norm) > len(common):
            print("Normalization helps! Need to strip/lower.")

if __name__ == "__main__":
    debug_mapping()
