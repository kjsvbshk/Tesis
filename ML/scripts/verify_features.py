#!/usr/bin/env python3
"""Script para verificar las features calculadas en Fase 2"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config
import pandas as pd

database_url = db_config.get_database_url()
ml_schema = db_config.get_schema("ml")

engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300, echo=False)

print("=" * 60)
print("🔍 Verificación de Features - Fase 2")
print("=" * 60)
print()

with engine.connect() as conn:
    conn.execute(text(f"SET search_path TO {ml_schema}, public"))
    conn.commit()
    
    # Verificar NULLs
    print("📊 Análisis de NULLs:")
    print("-" * 60)
    
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(home_ppg_last5) as with_ppg,
            COUNT(home_net_rating_last10) as with_net_rating,
            COUNT(home_rest_days) as with_rest,
            COUNT(home_injuries_count) as with_injuries,
            COUNT(implied_prob_home) as with_odds
        FROM ml.ml_ready_games
    """))
    row = result.fetchone()
    
    print(f"   Total registros: {row[0]}")
    print(f"   Con PPG last 5: {row[1]} ({100*row[1]/row[0]:.1f}%)")
    print(f"   Con Net Rating last 10: {row[2]} ({100*row[2]/row[0]:.1f}%)")
    print(f"   Con rest days: {row[3]} ({100*row[3]/row[0]:.1f}%)")
    print(f"   Con injuries count: {row[4]} ({100*row[4]/row[0]:.1f}%)")
    print(f"   Con implied prob: {row[5]} ({100*row[5]/row[0]:.1f}%)")
    print()
    
    # Muestra de datos
    print("📋 Muestra de datos (primeros 10 registros):")
    print("-" * 60)
    
    result = conn.execute(text("""
        SELECT 
            game_id, fecha, home_team, away_team,
            home_ppg_last5, away_ppg_last5,
            home_net_rating_last10, away_net_rating_last10,
            home_rest_days, away_rest_days,
            home_injuries_count, away_injuries_count
        FROM ml.ml_ready_games
        ORDER BY fecha DESC
        LIMIT 10
    """))
    
    rows = result.fetchall()
    for i, r in enumerate(rows, 1):
        print(f"\n   {i}. Game ID: {r[0]}, Fecha: {r[1]}")
        print(f"      {r[2]} vs {r[3]}")
        print(f"      PPG last 5: home={r[4]}, away={r[5]}")
        print(f"      Net Rating last 10: home={r[6]}, away={r[7]}")
        print(f"      Rest days: home={r[8]}, away={r[9]}")
        print(f"      Injuries: home={r[10]}, away={r[11]}")
    
    print()
    
    # Verificar valores no nulos
    print("📊 Valores no nulos por feature:")
    print("-" * 60)
    
    result = conn.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE home_ppg_last5 IS NOT NULL) as ppg_count,
            COUNT(*) FILTER (WHERE home_net_rating_last10 IS NOT NULL) as net_rating_count,
            COUNT(*) FILTER (WHERE home_rest_days IS NOT NULL) as rest_count,
            COUNT(*) FILTER (WHERE home_injuries_count IS NOT NULL) as injuries_count
        FROM ml.ml_ready_games
    """))
    row = result.fetchone()
    
    print(f"   Registros con PPG last 5: {row[0]}")
    print(f"   Registros con Net Rating last 10: {row[1]}")
    print(f"   Registros con rest days: {row[2]}")
    print(f"   Registros con injuries count: {row[3]}")
    print()

