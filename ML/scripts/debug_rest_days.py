#!/usr/bin/env python3
"""Debug rest_days calculation"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy import create_engine, text
from src.config import db_config

database_url = db_config.get_database_url()
ml_schema = db_config.get_schema("ml")
espn_schema = db_config.get_schema("espn")

engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300, echo=False)

with engine.connect() as conn:
    conn.execute(text(f"SET search_path TO {ml_schema}, {espn_schema}, public"))
    conn.commit()

# Cargar datos
games = pd.read_sql(f"SELECT * FROM {espn_schema}.games ORDER BY fecha", engine)
ml = pd.read_sql(f"SELECT * FROM {ml_schema}.ml_ready_games", engine)

# Usar nombres completos
games['home_team_norm'] = games['home_team']
games['away_team_norm'] = games['away_team']

# Calcular rest days
games_dates = games[['game_id', 'fecha', 'home_team_norm', 'away_team_norm']].copy()
games_dates['fecha'] = pd.to_datetime(games_dates['fecha'])
games_dates = games_dates.sort_values('fecha')

last_dates = {}
rest_home = []
rest_away = []

for _, row in games_dates.head(10).iterrows():
    gid = row['game_id']
    home = row['home_team_norm']
    away = row['away_team_norm']
    date = row['fecha']
    
    last_home = last_dates.get(home, None)
    last_away = last_dates.get(away, None)
    
    rest_home.append((date - last_home).days if last_home is not None else None)
    rest_away.append((date - last_away).days if last_away is not None else None)
    
    last_dates[home] = date
    last_dates[away] = date

rest_df = pd.DataFrame({
    'game_id': games_dates.head(10)['game_id'].values,
    'home_rest_days': rest_home,
    'away_rest_days': rest_away
})

print("Rest days calculados (primeros 10):")
print(rest_df.to_string())

print("\nGame IDs en ml_ready_games (primeros 10):")
print(ml[['game_id', 'home_team', 'away_team']].head(10).to_string())

# Intentar merge
ml_test = ml.head(10).copy()
merged = ml_test.merge(rest_df, on='game_id', how='left')
print("\nDespués del merge:")
print(merged[['game_id', 'home_team', 'home_rest_days', 'away_rest_days']].to_string())

