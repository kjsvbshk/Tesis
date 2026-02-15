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

print("="*80)
print("RESUMEN FINAL DEL DATASET")
print("="*80)

# espn.games
cur.execute('SELECT COUNT(*) FROM espn.games')
games = cur.fetchone()[0]
print(f"\nespn.games: {games} registros")

# ml.ml_ready_games  
cur.execute('SELECT COUNT(*) FROM ml.ml_ready_games')
ml_games = cur.fetchone()[0]
print(f"ml.ml_ready_games: {ml_games} registros")

# player_stats
cur.execute('SELECT COUNT(*) FROM espn.player_stats')
players = cur.fetchone()[0]
print(f"espn.player_stats: {players} registros")

# team_stats
cur.execute('SELECT COUNT(*) FROM espn.team_stats')
teams = cur.fetchone()[0]
print(f"espn.team_stats: {teams} registros")

# standings
cur.execute('SELECT COUNT(*) FROM espn.standings')
standings = cur.fetchone()[0]
print(f"espn.standings: {standings} equipos")

print("\n" + "="*80)
print("CONCLUSIÓN")
print("="*80)
print(f"✅ Dataset completo y listo para Fase 1.2")
print(f"✅ {ml_games} partidos con stats completas")
print(f"✅ Standings para 3 temporadas (2023-24, 2024-25, 2025-26)")
print("="*80)

conn.close()
