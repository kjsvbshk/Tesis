import sys
import os
import argparse
from datetime import datetime, timedelta

# Agregar el directorio actual al path para poder importar módulos de la app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, espn_engine
from sqlalchemy.orm import sessionmaker
from app.services.game_sync_service import GameSyncService
from app.services.cache_service import cache_service

def bulk_sync(start_date_str, end_date_str):
    print(f"Iniciando Bulk Sync desde {start_date_str} hasta {end_date_str}...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    if end_date < start_date:
        print("Error: end_date debe ser mayor o igual a start_date")
        return
        
    days_total = (end_date - start_date).days
    
    # Generar todas las fechas en el rango
    dates = [
        (start_date + timedelta(days=i)).strftime("%Y%m%d")
        for i in range(days_total + 1)
    ]
    
    print(f"Se consultarán {len(dates)} días en la API de ESPN.")
    
    # Crear sesión de base de datos
    EspnSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=espn_engine)
    db = EspnSessionLocal()
    
    try:
        service = GameSyncService(db)
        
        all_games = []
        fetch_errors = []
        
        # Consultar la API para cada fecha
        for i, date_str in enumerate(dates):
            print(f"[{i+1}/{len(dates)}] Consultando fecha {date_str}...", end=" ")
            try:
                games = service._fetch_games(date_str)
                all_games.extend(games)
                print(f"OK ({len(games)} partidos encontrados)")
            except Exception as e:
                print(f"ERROR: {e}")
                fetch_errors.append(f"{date_str}: {e}")
        
        synced = 0
        if all_games:
            print(f"Haciendo upsert de {len(all_games)} partidos en la base de datos...")
            synced = service._upsert_games(all_games)
            
            print("Invalidando cachés para actualizar UI...")
            cache_service.invalidate_pattern("matches")
            cache_service.invalidate_pattern("predictions_upcoming")
            
        print("\n--- RESUMEN DE BULK SYNC ---")
        print(f"Fechas consultadas: {start_date_str} al {end_date_str} ({len(dates)} días)")
        print(f"Partidos obtenidos: {len(all_games)}")
        print(f"Partidos guardados: {synced}")
        print(f"Errores de conexión: {len(fetch_errors)}")
        if fetch_errors:
            print("Detalle de errores:", fetch_errors)
            
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk Sync de partidos de NBA desde ESPN.")
    parser.add_argument("--start", type=str, default="2025-10-01", help="Fecha de inicio (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2026-06-30", help="Fecha de fin (YYYY-MM-DD)")
    
    args = parser.parse_args()
    bulk_sync(args.start, args.end)
