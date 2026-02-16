from sqlalchemy import create_engine, text
import sys
from pathlib import Path

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def inspect_schema():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- espn.team_stats columns ---")
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'espn' AND table_name = 'team_stats'"))
        for r in res:
            print(f"{r[0]}: {r[1]}")
            
        print("\n--- espn.games columns ---")
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'espn' AND table_name = 'games'"))
        for r in res:
            print(f"{r[0]}: {r[1]}")

        print("\n--- espn.nba_player_boxscores columns ---")
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'espn' AND table_name = 'nba_player_boxscores'"))
        for r in res:
            print(f"{r[0]}: {r[1]}")

if __name__ == "__main__":
    inspect_schema()
