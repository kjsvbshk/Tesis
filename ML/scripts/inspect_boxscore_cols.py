from sqlalchemy import create_engine, text
import sys
from pathlib import Path

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def inspect_cols():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- Columns in espn.nba_player_boxscores ---")
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'espn' AND table_name = 'nba_player_boxscores'"))
        for r in res:
            print(f"{r[0]}: {r[1]}")

if __name__ == "__main__":
    inspect_cols()
