from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Check CSV
csv_path = 'data/processed/nba_full_dataset.csv'
df = pd.read_csv(csv_path)
print("="*80)
print("CSV CONSOLIDADO")
print("="*80)
print(f"Total registros: {len(df)}")
print(f"Rango fechas: {df['fecha'].min()} a {df['fecha'].max()}")

# Check database
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    print("\n" + "="*80)
    print("BASE DE DATOS")
    print("="*80)
    
    # espn.games
    result = conn.execute(text('SELECT COUNT(*) FROM espn.games'))
    games_count = result.fetchone()[0]
    print(f"espn.games: {games_count} registros")
    
    # ml.ml_ready_games
    result = conn.execute(text('SELECT COUNT(*) FROM ml.ml_ready_games'))
    ml_count = result.fetchone()[0]
    print(f"ml.ml_ready_games: {ml_count} registros")
    
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    print(f"Boxscores scrapeados: 3,890")
    print(f"CSV consolidado (ETL): {len(df)} (-{3890-len(df)} filtrados)")
    print(f"Cargados a espn.games: {games_count}")
    print(f"Cargados a ml.ml_ready_games: {ml_count}")
    print("="*80)
