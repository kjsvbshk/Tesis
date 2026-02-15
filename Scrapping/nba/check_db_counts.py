from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    # Count games in espn.games
    result = conn.execute(text('SELECT COUNT(*) as count FROM espn.games'))
    games_count = result.fetchone()[0]
    
    # Count in ml.ml_ready_games
    result2 = conn.execute(text('SELECT COUNT(*) as count FROM ml.ml_ready_games'))
    ml_count = result2.fetchone()[0]
    
    print(f"espn.games: {games_count} registros")
    print(f"ml.ml_ready_games: {ml_count} registros")
