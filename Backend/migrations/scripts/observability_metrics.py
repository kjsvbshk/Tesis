#!/usr/bin/env python3
"""
Observabilidad - Métricas de Mapping y Reconciliación
Ejecutar periódicamente (cron) para monitorear salud del sistema

Uso:
    python migrations/scripts/observability_metrics.py
"""

import sys
import os
from sqlalchemy import create_engine, text
from datetime import datetime
from pathlib import Path

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Obtener variables de entorno
DB_HOST = os.getenv("NEON_DB_HOST") or os.getenv("DB_HOST")
DB_PORT = os.getenv("NEON_DB_PORT", "5432")
DB_NAME = os.getenv("NEON_DB_NAME") or os.getenv("DB_NAME")
DB_USER = os.getenv("NEON_DB_USER") or os.getenv("DB_USER")
DB_PASSWORD = os.getenv("NEON_DB_PASSWORD") or os.getenv("DB_PASSWORD")
DB_SSLMODE = os.getenv("NEON_DB_SSLMODE", "require")
DB_CHANNEL_BINDING = os.getenv("NEON_DB_CHANNEL_BINDING", "require")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?sslmode={DB_SSLMODE}&channel_binding={DB_CHANNEL_BINDING}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_metric(label, value, threshold=None, is_error=False):
    """Imprime métrica con formato"""
    if is_error:
        color = Colors.RED
        symbol = "❌"
    elif threshold and isinstance(value, (int, float)) and value > threshold:
        color = Colors.YELLOW
        symbol = "⚠️"
    else:
        color = Colors.GREEN
        symbol = "✅"
    
    print(f"{color}{symbol} {label}: {value}{Colors.RESET}")
    if threshold and isinstance(value, (int, float)) and value > threshold:
        print(f"   ⚠️  Threshold: {threshold}")

def main():
    """Calcular y mostrar métricas de observabilidad"""
    print("=" * 80)
    print("📊 MÉTRICAS DE OBSERVABILIDAD - FASE 4.2")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    with engine.connect() as conn:
        # ========================================================================
        # 1. MÉTRICAS DE MAPPING (odds_event_game_map)
        # ========================================================================
        print("1. MÉTRICAS DE MAPPING (odds_event_game_map)")
        print("-" * 80)
        
        # Total de odds sin mapping
        query1 = text("""
            SELECT 
                COUNT(DISTINCT o.external_event_id) as odds_sin_mapping,
                COUNT(DISTINCT o.external_event_id) * 100.0 / NULLIF(COUNT(DISTINCT o.external_event_id) + 
                    (SELECT COUNT(DISTINCT external_event_id) FROM espn.odds_event_game_map), 0) as porcentaje_sin_mapping
            FROM espn.odds o
            LEFT JOIN espn.odds_event_game_map m ON o.external_event_id = m.external_event_id
            WHERE m.external_event_id IS NULL
        """)
        result1 = conn.execute(query1).fetchone()
        if result1:
            odds_sin_mapping = result1[0] or 0
            porcentaje = result1[1] or 0
            print_metric("Odds sin mapping", f"{odds_sin_mapping} ({porcentaje:.2f}%)", threshold=10)
        
        # Mappings que necesitan revisión (solo si la columna existe)
        query2_check = text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'espn'
                AND table_name = 'odds_event_game_map'
                AND column_name = 'needs_review'
            )
        """)
        has_needs_review = conn.execute(query2_check).scalar()
        
        if has_needs_review:
            query2 = text("""
                SELECT COUNT(*) as needs_review_count,
                       COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM espn.odds_event_game_map), 0) as porcentaje
                FROM espn.odds_event_game_map
                WHERE needs_review = true
            """)
        else:
            query2 = text("SELECT 0 as needs_review_count, 0.0 as porcentaje")
        result2 = conn.execute(query2).fetchone()
        if result2:
            needs_review = result2[0] or 0
            porcentaje_review = result2[1] or 0
            print_metric("Mappings que necesitan revisión", f"{needs_review} ({porcentaje_review:.2f}%)", threshold=5)
        
        # Distribución de confianza
        query3 = text("""
            SELECT 
                resolution_confidence,
                COUNT(*) as count,
                COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM espn.odds_event_game_map), 0) as porcentaje
            FROM espn.odds_event_game_map
            GROUP BY resolution_confidence
            ORDER BY count DESC
        """)
        results3 = conn.execute(query3).fetchall()
        print("\n   Distribución de confianza:")
        for row in results3:
            conf = row[0] or 'NULL'
            count = row[1]
            pct = row[2] or 0
            print(f"     - {conf}: {count} ({pct:.2f}%)")
        
        # Distribución de métodos de resolución
        query4 = text("""
            SELECT 
                resolution_method,
                COUNT(*) as count
            FROM espn.odds_event_game_map
            GROUP BY resolution_method
            ORDER BY count DESC
        """)
        results4 = conn.execute(query4).fetchall()
        print("\n   Métodos de resolución:")
        for row in results4:
            method = row[0] or 'NULL'
            count = row[1]
            print(f"     - {method}: {count}")
        
        print()
        
        # ========================================================================
        # 2. MÉTRICAS DE RECONCILIACIÓN (espn.bets.user_id)
        # ========================================================================
        print("2. MÉTRICAS DE RECONCILIACIÓN (espn.bets.user_id)")
        print("-" * 80)
        
        # Bets huérfanos (user_id no existe en user_accounts)
        query5 = text("""
            SELECT COUNT(*) as orphaned_bets
            FROM espn.bets b
            LEFT JOIN app.user_accounts u ON u.id = b.user_id
            WHERE u.id IS NULL
        """)
        result5 = conn.execute(query5).fetchone()
        if result5:
            orphaned = result5[0] or 0
            is_error = orphaned > 0
            print_metric("Bets huérfanos (user_id no existe)", orphaned, is_error=is_error)
        
        # Total de bets
        query6 = text("SELECT COUNT(*) FROM espn.bets")
        total_bets = conn.execute(query6).scalar() or 0
        print_metric("Total de bets", total_bets)
        
        if total_bets > 0 and orphaned > 0:
            porcentaje_orphaned = (orphaned / total_bets) * 100
            print_metric("Porcentaje de bets huérfanos", f"{porcentaje_orphaned:.2f}%", threshold=0.1, is_error=orphaned > 0)
        
        print()
        
        # ========================================================================
        # 3. RESUMEN Y ALERTAS
        # ========================================================================
        print("=" * 80)
        print("📋 RESUMEN Y ALERTAS")
        print("=" * 80)
        
        alerts = []
        
        if result1 and (result1[0] or 0) > 10:
            alerts.append(f"⚠️  {result1[0]} odds sin mapping (>10)")
        
        if result2 and (result2[0] or 0) > 5:
            alerts.append(f"⚠️  {result2[0]} mappings necesitan revisión (>5)")
        
        if orphaned > 0:
            alerts.append(f"❌ {orphaned} bets huérfanos detectados (CRÍTICO)")
        
        if alerts:
            print("\n🚨 ALERTAS:")
            for alert in alerts:
                print(f"   {alert}")
        else:
            print("\n✅ No hay alertas. Sistema saludable.")
        
        print()
        print("=" * 80)

if __name__ == "__main__":
    main()
