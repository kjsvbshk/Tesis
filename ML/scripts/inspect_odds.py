#!/usr/bin/env python3
"""Inspeccionar estructura de odds para extraer probabilidades"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import json
from sqlalchemy import create_engine, text
from src.config import db_config

database_url = db_config.get_database_url()
espn_schema = db_config.get_schema("espn")

engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300, echo=False)

with engine.connect() as conn:
    conn.execute(text(f"SET search_path TO {espn_schema}, public"))
    conn.commit()

# Cargar odds
odds = pd.read_sql("SELECT * FROM espn.odds LIMIT 5", engine)

print("=" * 60)
print("🔍 Inspección de Estructura de Odds")
print("=" * 60)
print()

if not odds.empty:
    print(f"Total de registros: {len(odds)}")
    print(f"\nColumnas: {list(odds.columns)}")
    print()
    
    # Inspeccionar bookmakers
    if 'bookmakers' in odds.columns:
        print("📋 Estructura de bookmakers (primer registro):")
        print("-" * 60)
        
        first_bookmakers = odds.iloc[0]['bookmakers']
        if isinstance(first_bookmakers, str):
            try:
                first_bookmakers = json.loads(first_bookmakers)
            except:
                pass
        
        print(f"Tipo: {type(first_bookmakers)}")
        if isinstance(first_bookmakers, (dict, list)):
            print(f"Contenido (primeros 500 chars):")
            print(json.dumps(first_bookmakers, indent=2)[:500])
        else:
            print(f"Valor: {first_bookmakers}")
        
        print()
        
        # Intentar extraer odds
        print("💰 Intentando extraer odds:")
        print("-" * 60)
        
        for idx, row in odds.head(3).iterrows():
            print(f"\nRegistro {idx + 1}:")
            print(f"  game_id: {row.get('game_id')}")
            print(f"  home_team: {row.get('home_team')}")
            print(f"  away_team: {row.get('away_team')}")
            
            bookmakers = row.get('bookmakers')
            if bookmakers:
                if isinstance(bookmakers, str):
                    try:
                        bookmakers = json.loads(bookmakers)
                    except:
                        pass
                
                if isinstance(bookmakers, list) and len(bookmakers) > 0:
                    print(f"  Bookmakers encontrados: {len(bookmakers)}")
                    # Inspeccionar primer bookmaker
                    first_bm = bookmakers[0]
                    print(f"  Primer bookmaker: {json.dumps(first_bm, indent=4)[:300]}")
                elif isinstance(bookmakers, dict):
                    print(f"  Bookmakers (dict): {json.dumps(bookmakers, indent=2)[:300]}")
else:
    print("⚠️  No hay datos en la tabla odds")

