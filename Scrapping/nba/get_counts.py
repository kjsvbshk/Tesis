import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('NEON_DB_HOST'),
    port=os.getenv('NEON_DB_PORT'),
    database=os.getenv('NEON_DB_NAME'),
    user=os.getenv('NEON_DB_USER'),
    password=os.getenv('NEON_DB_PASSWORD'),
    sslmode='require'
)

cur = conn.cursor()

queries = {
    'espn.games': 'SELECT COUNT(*) FROM espn.games',
    'ml.ml_ready_games': 'SELECT COUNT(*) FROM ml.ml_ready_games',
    'espn.player_stats': 'SELECT COUNT(*) FROM espn.player_stats',
    'espn.team_stats': 'SELECT COUNT(*) FROM espn.team_stats',
    'espn.standings': 'SELECT COUNT(*) FROM espn.standings'
}

print("VERIFICACIÓN FINAL DEL DATASET")
print("="*60)

for table, query in queries.items():
    cur.execute(query)
    count = cur.fetchone()[0]
    print(f"{table}: {count}")

conn.close()
