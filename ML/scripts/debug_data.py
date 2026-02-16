from sqlalchemy import create_engine, text
import sys
from pathlib import Path

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def debug_data():
    engine = create_engine(db_config.get_database_url())
    game_id = 401584691
    with engine.connect() as conn:
        print(f"--- Debugging Game ID {game_id} ---")
        
        # Check Games table
        res = conn.execute(text(f"SELECT game_id, fecha, home_team, away_team, home_score, away_score, home_pts, away_pts FROM espn.games WHERE game_id = {game_id}"))
        game = res.fetchone()
        if game:
            print(f"Games Table: {game._asdict()}")
        else:
            print("Games Table: Not found")
            
        # Check Player Boxscores
        res = conn.execute(text(f"SELECT COUNT(*) FROM espn.nba_player_boxscores WHERE game_id = '{game_id}'"))
        count = res.fetchone()[0]
        print(f"Player Boxscores Count: {count}")
        
        if count > 0:
            res = conn.execute(text(f"SELECT team_tricode, SUM(pts) as team_pts FROM espn.nba_player_boxscores WHERE game_id = '{game_id}' GROUP BY team_tricode"))
            for r in res:
                print(f"  Team {r[0]}: {r[1]} pts")

        # Check Team Stats table (if used)
        res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema = 'espn' AND table_name = 'games'"))
        cols = [r[0] for r in res]
        print(f"Games columns available: {cols}")

if __name__ == "__main__":
    debug_data()
