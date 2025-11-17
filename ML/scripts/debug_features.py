#!/usr/bin/env python3
"""Script para debuggear por qué las features no se aplican"""

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

print("=" * 60)
print("🔍 Debug: Por qué las features no se aplican")
print("=" * 60)
print()

# Cargar datos
with engine.connect() as conn:
    conn.execute(text(f"SET search_path TO {ml_schema}, {espn_schema}, public"))
    conn.commit()

games = pd.read_sql(f"SELECT * FROM {espn_schema}.games ORDER BY fecha LIMIT 5", engine)
ml = pd.read_sql(f"SELECT * FROM {ml_schema}.ml_ready_games LIMIT 5", engine)

print("📋 Comparación de nombres de equipos:")
print("-" * 60)
print("\nPrimeros 5 partidos de espn.games:")
print(games[['game_id', 'home_team', 'home_team_normalized', 'away_team', 'away_team_normalized']].to_string())
print("\nPrimeros 5 partidos de ml.ml_ready_games:")
print(ml[['game_id', 'home_team', 'away_team']].to_string())

print("\n🔍 Verificando mapeo:")
print("-" * 60)

# Simular el proceso de rolling stats
if 'home_team_normalized' in games.columns:
    games['home_team_norm'] = games['home_team_normalized']
    games['away_team_norm'] = games['away_team_normalized']
else:
    games['home_team_norm'] = games['home_team']
    games['away_team_norm'] = games['away_team']

# Crear un registro de prueba
test_game_id = games.iloc[0]['game_id']
test_home = games.iloc[0]['home_team_norm']
test_away = games.iloc[0]['away_team_norm']

print(f"\nTest Game ID: {test_game_id}")
print(f"Home team (normalized): '{test_home}'")
print(f"Away team (normalized): '{test_away}'")

# Ver qué hay en ml_ready_games para este game_id
ml_test = ml[ml['game_id'] == test_game_id]
if not ml_test.empty:
    print(f"\nEn ml_ready_games:")
    print(f"  Home team: '{ml_test.iloc[0]['home_team']}'")
    print(f"  Away team: '{ml_test.iloc[0]['away_team']}'")
    
    print(f"\n¿Coinciden?")
    print(f"  Home: {test_home == ml_test.iloc[0]['home_team']}")
    print(f"  Away: {test_away == ml_test.iloc[0]['away_team']}")

# Ver todos los nombres únicos
print("\n📊 Nombres únicos de equipos:")
print("-" * 60)
print("\nEn espn.games (normalized):")
if 'home_team_normalized' in games.columns:
    unique_espn = set(games['home_team_normalized'].unique()) | set(games['away_team_normalized'].unique())
else:
    unique_espn = set(games['home_team'].unique()) | set(games['away_team'].unique())
print(f"  Total: {len(unique_espn)}")
print(f"  Ejemplos: {list(unique_espn)[:10]}")

print("\nEn ml.ml_ready_games:")
unique_ml = set(ml['home_team'].unique()) | set(ml['away_team'].unique())
print(f"  Total: {len(unique_ml)}")
print(f"  Ejemplos: {list(unique_ml)[:10]}")

print("\n¿Hay diferencias?")
diff = unique_espn - unique_ml
if diff:
    print(f"  En espn pero no en ml: {list(diff)[:10]}")
diff2 = unique_ml - unique_espn
if diff2:
    print(f"  En ml pero no en espn: {list(diff2)[:10]}")

