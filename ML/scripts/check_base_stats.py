from sqlalchemy import create_engine, text
import sys
from pathlib import Path
import pandas as pd

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def check_base_stats():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- Table Counts ---")
        try:
            ts_count = conn.execute(text("SELECT COUNT(*) FROM espn.team_stats")).scalar()
            print(f"espn.team_stats: {ts_count}")
        except Exception as e:
            print(f"espn.team_stats error: {e}")
            
        try:
            tsg_count = conn.execute(text("SELECT COUNT(*) FROM espn.team_stats_game")).scalar()
            print(f"espn.team_stats_game: {tsg_count}")
        except Exception as e:
            print(f"espn.team_stats_game error: {e}")

        print("\n--- ML Table Sample (Base Stats) ---")
        cols_to_check = [
            'home_fg_pct', 'home_reb', 'home_ast', 'home_tov',
            'away_fg_pct', 'away_reb', 'away_ast', 'away_tov',
            'net_rating_diff', 'reb_diff', 'ast_diff', 'tov_diff',
            'implied_prob_home'
        ]
        
        # Check null counts for these specific columns
        print(f"{'Column':<25} | {'Null Count':<10} | {'Total Rows':<10}")
        print("-" * 50)
        
        for col in cols_to_check:
            try:
                null_count = conn.execute(text(f"SELECT COUNT(*) FROM ml.ml_ready_games WHERE {col} IS NULL")).scalar()
                total_count = conn.execute(text(f"SELECT COUNT(*) FROM ml.ml_ready_games")).scalar()
                print(f"{col:<25} | {null_count:<10} | {total_count:<10}")
            except Exception as e:
                 print(f"{col:<25} | Error: {e}")

if __name__ == "__main__":
    check_base_stats()
