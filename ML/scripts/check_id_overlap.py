from sqlalchemy import create_engine, text
import sys
from pathlib import Path

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def check_id_overlap():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- Checking Game ID Formats ---")
        
        # ESPN Games sample
        res = conn.execute(text("SELECT game_id FROM espn.games LIMIT 5"))
        espn_ids = [str(r[0]) for r in res]
        print(f"ESPN Game IDs (sample): {espn_ids}")
        
        # Boxscores sample
        res = conn.execute(text("SELECT DISTINCT game_id FROM espn.nba_player_boxscores LIMIT 5"))
        box_ids = [str(r[0]) for r in res]
        print(f"Boxscore Game IDs (sample): {box_ids}")
        
        # Total match attempt
        res = conn.execute(text("""
            SELECT COUNT(*) 
            FROM espn.games g
            JOIN espn.nba_player_boxscores b ON g.game_id::text = b.game_id
        """))
        matches = res.fetchone()[0]
        print(f"Direct text matches: {matches}")
        
        # Check all tables in espn schema
        res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'espn'"))
        all_tables = [r[0] for r in res]
        print(f"All tables in espn schema: {all_tables}")
        
        # Audit team names in games
        res = conn.execute(text("SELECT DISTINCT team_name FROM (SELECT home_team as team_name FROM espn.games UNION SELECT away_team FROM espn.games) t ORDER BY team_name"))
        names = [r[0] for r in res]
        print(f"Total teams in games ({len(names)}):")
        print(", ".join(names))
        
        # Check LAC count specifically
        res = conn.execute(text("SELECT COUNT(*) FROM espn.nba_player_boxscores WHERE team_tricode = 'LAC'"))
        lac_count = res.fetchone()[0]
        print(f"\nLAC Count in boxscores: {lac_count}")
        
        # Check all tricodes
        res = conn.execute(text("SELECT DISTINCT team_tricode FROM espn.nba_player_boxscores"))
        all_tricodes = sorted([r[0] for r in res if r[0]])
        print(f"Total tricodes in boxscores ({len(all_tricodes)}):")
        print(", ".join(all_tricodes))

if __name__ == "__main__":
    check_id_overlap()
