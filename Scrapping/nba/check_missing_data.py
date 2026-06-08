"""
Diagnostic script to check row counts and season coverage in all tables.
"""
import psycopg2
from load_data import Config

def check_tables():
    config = Config()
    try:
        conn = psycopg2.connect(**config.db_config)
        cur = conn.cursor()
        
        tables = [
            'espn.games',
            'espn.standings',
            'espn.team_stats',
            'espn.player_stats',
            'espn.nba_player_boxscores',
            'espn.odds',
            'espn.game_odds',
            'espn.odds_event_game_map',
            'espn.game_id_mapping'
        ]
        
        print(f"{'Table':<30} | {'Count':<10} | {'Seasons/Notes'}")
        print("-" * 60)
        
        for table in tables:
            try:
                # Count
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                
                # Check for season/date info if available
                notes = ""
                if table == 'espn.game_id_mapping':
                    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE season IS NULL")
                    null_season = cur.fetchone()[0]
                    notes = f"Null seasons: {null_season}"
                elif table == 'espn.standings':
                     cur.execute(f"SELECT COUNT(DISTINCT season) FROM {table}")
                     seasons = cur.fetchone()[0]
                     notes = f"Seasons: {seasons}"
                elif table == 'espn.nba_player_boxscores':
                    # Check distinct years from date
                    cur.execute(f"SELECT MIN(game_date), MAX(game_date) FROM {table}")
                    min_d, max_d = cur.fetchone()
                    notes = f"{min_d} to {max_d}"
                
                print(f"{table:<30} | {count:<10} | {notes}")
            except Exception as e:
                print(f"{table:<30} | {'ERROR':<10} | {str(e).splitlines()[0]}")
                conn.rollback()
        
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    check_tables()
