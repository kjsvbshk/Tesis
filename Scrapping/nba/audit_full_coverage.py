"""
Auditoría completa del dataset NBA: cobertura de partidos y mapping.

Muestra:
  - Cuántos partidos hay en espn.games por temporada/tipo
  - Cuántos tienen score (jugados)
  - Cuántos tienen mapping ESPN→NBA
  - Cuántos tienen boxscores de jugadores (off_rating, etc.)
  - Estimado de partidos esperados vs. encontrados

Uso:
    python audit_full_coverage.py
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ML"))
from src.config import db_config


def run_audit():
    database_url = db_config.get_database_url()
    espn_schema  = db_config.get_schema("espn")
    ml_schema    = db_config.get_schema("ml")
    engine = create_engine(database_url, pool_pre_ping=True)

    print("=" * 70)
    print("AUDITORÍA COMPLETA DE COBERTURA NBA")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # 1. Estado general de espn.games
    # -----------------------------------------------------------------------
    print("\n1. COBERTURA EN espn.games")
    print("-" * 70)
    rows = pd.read_sql(text(f"""
        SELECT
            CASE
                WHEN fecha >= '2023-10-24' AND fecha < '2024-09-01' THEN '2023-24'
                WHEN fecha >= '2024-10-22' AND fecha < '2025-09-01' THEN '2024-25'
                WHEN fecha >= '2025-10-22'                           THEN '2025-26'
                ELSE 'otro'
            END AS season,
            COUNT(*)                                                   AS total,
            SUM(CASE WHEN home_score > 0 OR away_score > 0 THEN 1 ELSE 0 END) AS jugados,
            SUM(CASE WHEN home_score = 0 AND away_score = 0 THEN 1 ELSE 0 END) AS pendientes
        FROM {espn_schema}.games
        GROUP BY 1
        ORDER BY 1
    """), engine)

    # Partidos esperados por temporada (regular + playoffs)
    expected = {
        "2023-24": 1320,   # ~1230 regular + 90 playoffs
        "2024-25": 1320,
        "2025-26": 900,    # ~820 jugados hasta Mar 2026 + futuros hasta abr
        "otro": 0,
    }

    print(f"{'Temporada':<12} {'Total':>8} {'Jugados':>10} {'Pendientes':>12} {'Esperado':>10} {'Cobertura':>10}")
    print("-" * 70)
    for _, r in rows.iterrows():
        exp = expected.get(r["season"], "?")
        cov = f"{r['total']/exp*100:.0f}%" if isinstance(exp, int) and exp > 0 else "N/A"
        print(f"{r['season']:<12} {r['total']:>8} {r['jugados']:>10} {r['pendientes']:>12} {exp:>10} {cov:>10}")

    # -----------------------------------------------------------------------
    # 2. Cobertura de mapping
    # -----------------------------------------------------------------------
    print("\n2. COBERTURA DE game_id_mapping")
    print("-" * 70)
    mapping_rows = pd.read_sql(text(f"""
        SELECT
            CASE
                WHEN g.fecha >= '2023-10-24' AND g.fecha < '2024-09-01' THEN '2023-24'
                WHEN g.fecha >= '2024-10-22' AND g.fecha < '2025-09-01' THEN '2024-25'
                WHEN g.fecha >= '2025-10-22'                             THEN '2025-26'
                ELSE 'otro'
            END AS season,
            COUNT(g.game_id)                                             AS total_jugados,
            COUNT(m.espn_id)                                             AS con_mapping,
            COUNT(g.game_id) - COUNT(m.espn_id)                         AS sin_mapping
        FROM {espn_schema}.games g
        LEFT JOIN {espn_schema}.game_id_mapping m ON g.game_id::text = m.espn_id
        WHERE g.home_score > 0 OR g.away_score > 0
        GROUP BY 1
        ORDER BY 1
    """), engine)

    print(f"{'Temporada':<12} {'Jugados':>10} {'Con mapping':>14} {'Sin mapping':>12} {'Cobertura':>10}")
    print("-" * 70)
    for _, r in mapping_rows.iterrows():
        cov = f"{r['con_mapping']/r['total_jugados']*100:.1f}%" if r['total_jugados'] > 0 else "N/A"
        print(f"{r['season']:<12} {r['total_jugados']:>10} {r['con_mapping']:>14} {r['sin_mapping']:>12} {cov:>10}")

    # -----------------------------------------------------------------------
    # 3. Cobertura de off_rating en ml_ready_games
    # -----------------------------------------------------------------------
    print("\n3. COBERTURA DE off_rating_rolling EN ml.ml_ready_games")
    print("-" * 70)
    try:
        off_rows = pd.read_sql(text(f"""
            SELECT
                CASE
                    WHEN fecha >= '2023-10-24' AND fecha < '2024-09-01' THEN '2023-24'
                    WHEN fecha >= '2024-10-22' AND fecha < '2025-09-01' THEN '2024-25'
                    WHEN fecha >= '2025-10-22'                           THEN '2025-26'
                    ELSE 'otro'
                END AS season,
                COUNT(*)                                                          AS total,
                SUM(CASE WHEN off_rating_diff IS NOT NULL THEN 1 ELSE 0 END)     AS con_off_rating,
                SUM(CASE WHEN off_rating_diff IS NULL THEN 1 ELSE 0 END)          AS sin_off_rating
            FROM {ml_schema}.ml_ready_games
            WHERE home_win IS NOT NULL
              AND (home_score > 0 OR away_score > 0)
            GROUP BY 1
            ORDER BY 1
        """), engine)

        print(f"{'Temporada':<12} {'Total':>8} {'Con off_rating':>16} {'Sin off_rating':>15} {'Cobertura':>10}")
        print("-" * 70)
        for _, r in off_rows.iterrows():
            cov = f"{r['con_off_rating']/r['total']*100:.1f}%" if r['total'] > 0 else "N/A"
            print(f"{r['season']:<12} {r['total']:>8} {r['con_off_rating']:>16} {r['sin_off_rating']:>15} {cov:>10}")
    except Exception as e:
        print(f"  Error consultando ml_ready_games: {e}")

    # -----------------------------------------------------------------------
    # 4. Sample de ESPN games sin mapping
    # -----------------------------------------------------------------------
    print("\n4. MUESTRA DE ESPN GAMES SIN MAPPING (primeros 10)")
    print("-" * 70)
    sample = pd.read_sql(text(f"""
        SELECT g.game_id::text AS espn_id, g.fecha, g.home_team, g.away_team,
               g.home_score, g.away_score
        FROM {espn_schema}.games g
        LEFT JOIN {espn_schema}.game_id_mapping m ON g.game_id::text = m.espn_id
        WHERE m.espn_id IS NULL
          AND (g.home_score > 0 OR g.away_score > 0)
        ORDER BY g.fecha
        LIMIT 10
    """), engine)

    if sample.empty:
        print("  ¡Todos los juegos jugados tienen mapping!")
    else:
        for _, r in sample.iterrows():
            print(f"  ESPN {r['espn_id']}  {r['fecha']}  {r['away_team']} @ {r['home_team']}  "
                  f"{r['away_score']}-{r['home_score']}")

    # -----------------------------------------------------------------------
    # 5. Resumen final y recomendaciones
    # -----------------------------------------------------------------------
    print("\n5. RESUMEN Y PRÓXIMOS PASOS")
    print("-" * 70)

    total_jugados = mapping_rows["total_jugados"].sum()
    total_sin_map = mapping_rows["sin_mapping"].sum()
    pct_mapped    = (total_jugados - total_sin_map) / total_jugados * 100 if total_jugados > 0 else 0

    print(f"  Total partidos jugados:  {total_jugados}")
    print(f"  Con mapping:             {total_jugados - total_sin_map} ({pct_mapped:.1f}%)")
    print(f"  Sin mapping:             {int(total_sin_map)} ({100-pct_mapped:.1f}%)")

    if total_sin_map > 0:
        print(f"\n  --> Ejecutar: python fix_game_id_mapping.py")
        print(f"      (mejorará off_rating_rolling para ~{int(total_sin_map)} partidos)")

    print(f"\n  --> Para llenar partidos faltantes:")
    print(f"      python espn/populate_all_games.py --audit-only   # verificar")
    print(f"      python espn/populate_all_games.py                # llenar")
    print("=" * 70)


if __name__ == "__main__":
    run_audit()
