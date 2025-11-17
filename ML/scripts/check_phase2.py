#!/usr/bin/env python3
"""Checks finales de la Fase 2"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config

database_url = db_config.get_database_url()
ml_schema = db_config.get_schema("ml")

engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300, echo=False)

print("=" * 60)
print("✅ CHECKS FINALES - FASE 2")
print("=" * 60)
print()

with engine.connect() as conn:
    conn.execute(text(f"SET search_path TO {ml_schema}, public"))
    conn.commit()
    
    # Check 1: SELECT home_ppg_last5, away_ppg_last5 FROM ml.ml_ready_games LIMIT 10;
    print("📊 Check 1: Muestra de PPG last 5")
    print("-" * 60)
    result = conn.execute(text("""
        SELECT home_ppg_last5, away_ppg_last5 
        FROM ml.ml_ready_games 
        LIMIT 10
    """))
    rows = result.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"   {i}. Home PPG: {row[0]}, Away PPG: {row[1]}")
    print()
    
    # Check 2: SELECT COUNT(*) FROM ml.ml_ready_games WHERE home_ppg_last5 IS NULL;
    print("📊 Check 2: Conteo de NULLs en home_ppg_last5")
    print("-" * 60)
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ml.ml_ready_games 
        WHERE home_ppg_last5 IS NULL
    """))
    null_count = result.fetchone()[0]
    total = conn.execute(text("SELECT COUNT(*) FROM ml.ml_ready_games")).fetchone()[0]
    print(f"   Registros con home_ppg_last5 NULL: {null_count} de {total}")
    print(f"   Porcentaje: {100*null_count/total:.2f}%")
    if null_count == 0:
        print("   ✅ Todos los registros tienen PPG last 5")
    elif null_count < total * 0.1:
        print("   ✅ Menos del 10% son NULL (esperado al principio)")
    else:
        print("   ⚠️  Muchos NULLs, revisar")
    print()
    
    # Check 3: Resumen completo de todas las features
    print("📊 Check 3: Resumen completo de features")
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
    
    print(f"   Total de registros: {row[0]}")
    print(f"   Con PPG last 5: {row[1]} ({100*row[1]/row[0]:.1f}%)")
    print(f"   Con Net Rating last 10: {row[2]} ({100*row[2]/row[0]:.1f}%)")
    print(f"   Con rest days: {row[3]} ({100*row[3]/row[0]:.1f}%)")
    print(f"   Con injuries count: {row[4]} ({100*row[4]/row[0]:.1f}%)")
    print(f"   Con implied prob: {row[5]} ({100*row[5]/row[0]:.1f}%)")
    print()
    
    # Check 4: Muestra completa de un registro
    print("📋 Check 4: Muestra completa de un registro")
    print("-" * 60)
    result = conn.execute(text("""
        SELECT 
            game_id, fecha, home_team, away_team,
            home_ppg_last5, away_ppg_last5,
            home_net_rating_last10, away_net_rating_last10,
            home_rest_days, away_rest_days,
            home_injuries_count, away_injuries_count,
            implied_prob_home, implied_prob_away
        FROM ml.ml_ready_games
        WHERE home_ppg_last5 IS NOT NULL
        ORDER BY fecha DESC
        LIMIT 3
    """))
    rows = result.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"\n   Registro {i}:")
        print(f"      Game ID: {row[0]}, Fecha: {row[1]}")
        print(f"      {row[2]} vs {row[3]}")
        print(f"      PPG last 5: home={row[4]:.2f}, away={row[5]:.2f}")
        print(f"      Net Rating last 10: home={row[6]:.2f}, away={row[7]:.2f}")
        print(f"      Rest days: home={row[8]}, away={row[9]}")
        print(f"      Injuries: home={row[10]}, away={row[11]}")
        print(f"      Implied prob: home={row[12]}, away={row[13]}")
    print()
    
    print("=" * 60)
    print("✅ CHECKS COMPLETADOS")
    print("=" * 60)

