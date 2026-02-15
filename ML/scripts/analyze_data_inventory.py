#!/usr/bin/env python3
"""Script para analizar datos disponibles y recomendar expansión del dataset"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config

def main():
    engine = create_engine(db_config.get_database_url())
    
    print("=" * 80)
    print("📊 ANÁLISIS DE DATOS DISPONIBLES PARA EXPANSIÓN DEL DATASET")
    print("=" * 80)
    print()
    
    with engine.connect() as conn:
        # 1. Partidos en espn.games
        print("🏀 PARTIDOS DISPONIBLES (espn.games)")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                MIN(fecha) as min_fecha,
                MAX(fecha) as max_fecha,
                COUNT(DISTINCT EXTRACT(YEAR FROM fecha)) as years
            FROM espn.games
        """))
        row = result.fetchone()
        print(f"  Total partidos: {row[0]:,}")
        print(f"  Rango: {row[1]} a {row[2]}")
        print(f"  Años únicos: {row[3]}")
        print()
        
        # Partidos por año
        print("  Partidos por año:")
        result = conn.execute(text("""
            SELECT 
                EXTRACT(YEAR FROM fecha) as year,
                COUNT(*) as count
            FROM espn.games
            GROUP BY EXTRACT(YEAR FROM fecha)
            ORDER BY year DESC
        """))
        for year, count in result.fetchall():
            print(f"    {int(year)}: {count:,} partidos")
        print()
        
        # 2. Partidos en ml_ready_games
        print("🤖 PARTIDOS EN ML_READY_GAMES")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT COUNT(*) FROM ml.ml_ready_games
        """))
        ml_count = result.fetchone()[0]
        print(f"  Total: {ml_count:,} partidos")
        print()
        
        # 3. Odds disponibles
        print("💰 ODDS DISPONIBLES")
        print("-" * 80)
        
        # Verificar tabla game_odds
        result = conn.execute(text("""
            SELECT COUNT(*), COUNT(DISTINCT game_id)
            FROM espn.game_odds
        """))
        row = result.fetchone()
        print(f"  Registros en game_odds: {row[0]:,}")
        print(f"  Partidos con odds: {row[1]:,}")
        
        # Cobertura de odds
        result = conn.execute(text("""
            SELECT 
                COUNT(DISTINCT g.game_id) as total_games,
                COUNT(DISTINCT o.game_id) as games_with_odds
            FROM espn.games g
            LEFT JOIN espn.game_odds o ON g.game_id = o.game_id
        """))
        row = result.fetchone()
        coverage = (row[1] / row[0] * 100) if row[0] > 0 else 0
        print(f"  Cobertura: {row[1]:,}/{row[0]:,} ({coverage:.2f}%)")
        print()
        
        # 4. Player stats
        print("👤 PLAYER STATS")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT COUNT(*), COUNT(DISTINCT player_id)
            FROM espn.player_stats
        """))
        row = result.fetchone()
        print(f"  Total registros: {row[0]:,}")
        print(f"  Jugadores únicos: {row[1]:,}")
        print()
        
        # 5. Team stats
        print("🏆 TEAM STATS")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT COUNT(*), COUNT(DISTINCT team_id)
            FROM espn.team_stats_game
        """))
        row = result.fetchone()
        print(f"  Total registros: {row[0]:,}")
        print(f"  Equipos únicos: {row[1]:,}")
        print()
        
        # 6. Recomendaciones
        print("=" * 80)
        print("💡 RECOMENDACIONES")
        print("=" * 80)
        print()
        
        print("1. PROBLEMA PRINCIPAL: Dataset muy pequeño (1,237 partidos)")
        print("   • Todos los partidos son de la misma fecha (2025-11-09)")
        print("   • Esto sugiere que solo hay datos de UN DÍA")
        print("   ⚠️  CRÍTICO: Necesitamos datos históricos de múltiples temporadas")
        print()
        
        print("2. ACCIÓN INMEDIATA: Ejecutar scraping de datos históricos")
        print("   • Temporada 2024-2025 completa")
        print("   • Temporada 2023-2024 completa")
        print("   • Objetivo mínimo: 2,000-3,000 partidos")
        print()
        
        print("3. ODDS: Cobertura muy baja")
        print(f"   • Actual: {coverage:.2f}%")
        print("   • Ejecutar API para extraer odds históricos")
        print("   • Priorizar partidos más recientes (test set)")
        print()
        
        print("4. FEATURES ADICIONALES:")
        print("   • Player stats disponibles - considerar features de jugadores clave")
        print("   • Team stats disponibles - usar para features avanzadas")
        print()
        
        print("=" * 80)
        print("🚨 CONCLUSIÓN: DATASET INSUFICIENTE PARA MODELADO")
        print("=" * 80)
        print()
        print("El dataset actual (1,237 partidos de un solo día) NO es suficiente")
        print("para entrenar modelos predictivos robustos.")
        print()
        print("RECOMENDACIÓN: Pausar Fase 1.2 y ejecutar scraping de datos históricos")
        print("antes de continuar con el desarrollo del modelo.")
        print()


if __name__ == "__main__":
    main()
