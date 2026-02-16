from sqlalchemy import create_engine, text
import sys
from pathlib import Path

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def verify_stats():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- Verification of Base Stats in ml.ml_ready_games ---")
        
        total_rows = conn.execute(text("SELECT COUNT(*) FROM ml.ml_ready_games")).scalar()
        print(f"Total Rows: {total_rows}")
        
        cols = ['home_fg_pct', 'reb_diff', 'ast_diff', 'home_reb', 'implied_prob_home']
        
        for col in cols:
            non_null = conn.execute(text(f"SELECT COUNT(*) FROM ml.ml_ready_games WHERE {col} IS NOT NULL")).scalar()
            pct = (non_null / total_rows) * 100 if total_rows > 0 else 0
            print(f"{col:<20}: {non_null} non-null ({pct:.1f}%)")

if __name__ == "__main__":
    verify_stats()
