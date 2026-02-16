from sqlalchemy import create_engine, text
import sys
from pathlib import Path
import pandas as pd

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import db_config

def inspect_injuries():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        print("--- Inspecting espn.injuries ---")
        
        # Check count
        try:
            count = conn.execute(text("SELECT COUNT(*) FROM espn.injuries")).scalar()
            print(f"Total Rows: {count}")
            
            if count > 0:
                # Get columns
                cols = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'espn' AND table_name = 'injuries'")).fetchall()
                print("\nColumns:")
                for c in cols:
                    print(f" - {c[0]} ({c[1]})")
                
                # Sample data
                print("\nSample Data:")
                df = pd.read_sql("SELECT * FROM espn.injuries LIMIT 5", conn)
                print(df.to_string())
                
                # Check teams in injuries vs teams in games
                print("\nUnique Teams in Injuries:")
                teams = pd.read_sql("SELECT DISTINCT team_tricode FROM espn.injuries", conn) # Assuming team_tricode exists based on schema convention, or try generic
                if 'team_tricode' not in df.columns:
                     # Fallback if team_tricode doesn't exist, check other potential team cols
                     team_col = next((c for c in df.columns if 'team' in c), None)
                     if team_col:
                        teams = pd.read_sql(f"SELECT DISTINCT {team_col} FROM espn.injuries", conn)
                        print(f" (Using column: {team_col})")
                
                print(teams.head(10).values.flatten())

            else:
                print("Table is empty.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    inspect_injuries()
