"""
Poblar espn.games con TODOS los partidos de las temporadas 2023-24, 2024-25 y 2025-26.

Usa la ESPN Scoreboard JSON API (estable, no HTML scraping):
  https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD

Para cada fecha en el rango de cada temporada:
  1. Obtiene todos los game_ids del día
  2. Para cada juego nuevo (no está en la DB), llama al endpoint /summary para obtener
     equipos, scores y estado
  3. Inserta en espn.games; si el juego ya existe, opcionalmente actualiza el score

Temporadas:
  - 2023-24 regular + playoffs: 2023-10-24 a 2024-06-17
  - 2024-25 regular + playoffs: 2024-10-22 a 2025-06-22
  - 2025-26 regular:            2025-10-22 a hoy

Uso:
    python populate_all_games.py               # modo completo (todas las temporadas)
    python populate_all_games.py --audit-only  # solo muestra qué falta, no inserta
    python populate_all_games.py --since 2025-10-22   # solo desde esta fecha
    python populate_all_games.py --season 2025-26     # solo esta temporada
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import date, timedelta, datetime

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

# Agregar raíz del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ML"))
from src.config import db_config


ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_SUMMARY_URL    = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NBA-thesis-scraper/1.0)",
    "Accept": "application/json",
}
SLEEP_BETWEEN_REQUESTS = 0.4   # segundos entre llamadas

# ---------------------------------------------------------------------------
# Rangos de fechas por temporada (regular + playoffs)
# ---------------------------------------------------------------------------
SEASON_RANGES = {
    "2023-24": (date(2023, 10, 24), date(2024, 6, 17)),
    "2024-25": (date(2024, 10, 22), date(2025, 6, 22)),
    "2025-26": (date(2025, 10, 22), date.today()),
}


# ---------------------------------------------------------------------------
# Helpers ESPN API
# ---------------------------------------------------------------------------

def fetch_game_ids_for_date(day: date) -> list[str]:
    """Devuelve los game_ids ESPN para una fecha (usa scoreboard API)."""
    date_str = day.strftime("%Y%m%d")
    try:
        resp = requests.get(
            ESPN_SCOREBOARD_URL,
            params={"dates": date_str, "limit": 20},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.debug(f"  Error scoreboard {date_str}: {e}")
        return []

    game_ids = []
    for event in data.get("events", []):
        gid = event.get("id")
        if gid:
            game_ids.append(str(gid))
    return game_ids


def fetch_game_summary(game_id: str) -> dict | None:
    """
    Obtiene datos básicos de un partido via endpoint /summary.
    Devuelve dict con home_team, away_team, home_score, away_score, completed.
    """
    try:
        resp = requests.get(
            ESPN_SUMMARY_URL,
            params={"event": game_id},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.debug(f"  Error summary {game_id}: {e}")
        return None

    try:
        header = data["header"]
        comp   = header["competitions"][0]
        comps  = comp["competitors"]

        home = next(c for c in comps if c["homeAway"] == "home")
        away = next(c for c in comps if c["homeAway"] == "away")

        status    = comp.get("status", {}).get("type", {})
        completed = status.get("completed", False)

        home_score = int(home.get("score") or 0)
        away_score = int(away.get("score") or 0)

        # Obtener la fecha del partido
        fecha_raw = comp.get("date") or header.get("gameDate") or ""
        if fecha_raw:
            fecha = pd.to_datetime(fecha_raw).date()
        else:
            fecha = None

        # Determinar game_type desde season type
        season = header.get("season", {})
        season_type = season.get("type", 2)  # 1=preseason, 2=regular, 3=playoffs
        game_type = {1: "preseason", 2: "regular", 3: "playoffs"}.get(season_type, "regular")

        return {
            "game_id":    game_id,
            "fecha":      fecha,
            "home_team":  home["team"].get("displayName", ""),
            "away_team":  away["team"].get("displayName", ""),
            "home_score": home_score,
            "away_score": away_score,
            "completed":  completed,
            "game_type":  game_type,
        }
    except (KeyError, StopIteration, ValueError, TypeError) as e:
        logger.debug(f"  Error parseando summary {game_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_existing_game_ids(engine, espn_schema: str) -> set[str]:
    """Devuelve todos los game_ids que ya están en espn.games."""
    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT game_id::text FROM {espn_schema}.games")).fetchall()
    return {r[0] for r in rows}


def insert_game(conn, espn_schema: str, g: dict):
    """Inserta un partido nuevo en espn.games."""
    home_win = None
    if g["completed"] and g["home_score"] > 0:
        home_win = 1 if g["home_score"] > g["away_score"] else 0

    conn.execute(text(f"""
        INSERT INTO {espn_schema}.games
            (game_id, fecha, home_team, away_team, home_score, away_score, home_win, game_type)
        VALUES
            (:gid, :fecha, :ht, :at, :hs, :as_, :hw, :gt)
        ON CONFLICT (game_id) DO NOTHING
    """), {
        "gid":   g["game_id"],
        "fecha":  g["fecha"],
        "ht":    g["home_team"],
        "at":    g["away_team"],
        "hs":    g["home_score"] if g["completed"] else 0,
        "as_":   g["away_score"] if g["completed"] else 0,
        "hw":    home_win,
        "gt":    g["game_type"],
    })


def get_games_schema_columns(engine, espn_schema: str) -> set[str]:
    """Devuelve las columnas existentes de espn.games."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = 'games'
        """), {"schema": espn_schema}).fetchall()
    return {r[0] for r in rows}


# ---------------------------------------------------------------------------
# Lógica principal
# ---------------------------------------------------------------------------

def audit_coverage(engine, espn_schema: str) -> dict:
    """Imprime un resumen del estado actual de cobertura."""
    print("\n" + "=" * 60)
    print("AUDITORÍA DE COBERTURA DE PARTIDOS")
    print("=" * 60)

    existing = get_existing_game_ids(engine, espn_schema)
    print(f"Total game_ids en espn.games: {len(existing)}")

    # Por temporada (usando la fecha)
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT
                CASE
                    WHEN fecha >= '2023-10-24' AND fecha < '2024-09-01' THEN '2023-24'
                    WHEN fecha >= '2024-10-22' AND fecha < '2025-09-01' THEN '2024-25'
                    WHEN fecha >= '2025-10-22' THEN '2025-26'
                    ELSE 'otro'
                END AS season,
                COUNT(*) AS total,
                SUM(CASE WHEN home_score > 0 OR away_score > 0 THEN 1 ELSE 0 END) AS con_score,
                SUM(CASE WHEN home_score = 0 AND away_score = 0 THEN 1 ELSE 0 END) AS sin_score
            FROM {espn_schema}.games
            GROUP BY 1
            ORDER BY 1
        """)).fetchall()

    print(f"\n{'Temporada':<12} {'Total':>8} {'Con score':>12} {'Sin score':>10}")
    print("-" * 44)
    for r in rows:
        print(f"{r[0]:<12} {r[1]:>8} {r[2]:>12} {r[3]:>10}")

    # Mapping coverage
    with engine.connect() as conn:
        mapped = conn.execute(text(
            f"SELECT COUNT(*) FROM {espn_schema}.game_id_mapping"
        )).scalar()
    print(f"\nespn.game_id_mapping: {mapped} entradas ({mapped}/{len(existing)} = {mapped/len(existing)*100:.1f}%)")

    return {"total": len(existing), "mapped": mapped}


def populate_season(
    engine, espn_schema: str, season: str,
    dry_run: bool = False,
    season_ranges: dict | None = None,
) -> dict:
    """
    Itera todas las fechas de la temporada y llena los partidos faltantes.
    Devuelve estadísticas de lo procesado.
    """
    ranges = season_ranges or SEASON_RANGES
    start_date, end_date = ranges[season]
    existing = get_existing_game_ids(engine, espn_schema)
    columns = get_games_schema_columns(engine, espn_schema)

    has_game_type = "game_type" in columns

    print(f"\n--- Temporada {season}: {start_date} → {end_date} ---")
    print(f"  Partidos existentes en DB: {len(existing)}")

    # Recolectar todos los game_ids del período
    total_days = (end_date - start_date).days + 1
    all_espn_ids: dict[str, date] = {}  # game_id -> fecha del scoreboard

    print(f"  Consultando scoreboard para {total_days} fechas...")
    current = start_date
    while current <= end_date:
        gids = fetch_game_ids_for_date(current)
        for gid in gids:
            all_espn_ids[gid] = current
        current += timedelta(days=1)
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    print(f"  Total game_ids ESPN encontrados: {len(all_espn_ids)}")

    missing = {gid: d for gid, d in all_espn_ids.items() if gid not in existing}
    print(f"  Partidos faltantes en DB: {len(missing)}")

    if not missing:
        print("  Nada que insertar.")
        return {"season": season, "found": len(all_espn_ids), "inserted": 0, "errors": 0}

    inserted = 0
    errors = 0

    with engine.begin() as conn:
        for i, (gid, fallback_date) in enumerate(missing.items(), 1):
            summary = fetch_game_summary(gid)
            time.sleep(SLEEP_BETWEEN_REQUESTS)

            if summary is None:
                # Insertar como partido futuro con datos mínimos
                summary = {
                    "game_id":    gid,
                    "fecha":      fallback_date,
                    "home_team":  "",
                    "away_team":  "",
                    "home_score": 0,
                    "away_score": 0,
                    "completed":  False,
                    "game_type":  "regular",
                }

            if dry_run:
                status = "jugado" if summary["completed"] else "futuro"
                logger.info(f"  [{i}/{len(missing)}] {gid} {summary['fecha']} "
                            f"{summary['away_team']} @ {summary['home_team']} [{status}] [DRY RUN]")
                inserted += 1
                continue

            try:
                if not has_game_type:
                    # Insertar sin columna game_type
                    home_win = None
                    if summary["completed"] and summary["home_score"] > 0:
                        home_win = 1 if summary["home_score"] > summary["away_score"] else 0
                    conn.execute(text(f"""
                        INSERT INTO {espn_schema}.games
                            (game_id, fecha, home_team, away_team, home_score, away_score, home_win)
                        VALUES (:gid, :fecha, :ht, :at, :hs, :as_, :hw)
                        ON CONFLICT (game_id) DO NOTHING
                    """), {
                        "gid":  summary["game_id"],
                        "fecha": summary["fecha"],
                        "ht":   summary["home_team"],
                        "at":   summary["away_team"],
                        "hs":   summary["home_score"] if summary["completed"] else 0,
                        "as_":  summary["away_score"] if summary["completed"] else 0,
                        "hw":   home_win,
                    })
                else:
                    insert_game(conn, espn_schema, summary)

                status = "jugado" if summary["completed"] else "futuro"
                logger.info(f"  [{i}/{len(missing)}] Insertado {gid} {summary['fecha']} "
                            f"{summary['away_team']} @ {summary['home_team']} [{status}]")
                inserted += 1
            except Exception as e:
                logger.error(f"  [{i}/{len(missing)}] Error insertando {gid}: {e}")
                errors += 1

    return {"season": season, "found": len(all_espn_ids), "inserted": inserted, "errors": errors}


def populate_all_games(
    seasons: list[str] | None = None,
    since: str | None = None,
    dry_run: bool = False,
    audit_only: bool = False,
):
    """Función principal — llena todos los partidos faltantes."""
    database_url = db_config.get_database_url()
    espn_schema  = db_config.get_schema("espn")
    engine = create_engine(database_url, pool_pre_ping=True)

    # Auditoría inicial
    audit_coverage(engine, espn_schema)

    if audit_only:
        return

    # Seleccionar temporadas
    if seasons is None:
        seasons = list(SEASON_RANGES.keys())

    # Construir rangos efectivos (aplicar filtro --since si se indicó)
    effective_ranges = dict(SEASON_RANGES)
    if since:
        since_date = date.fromisoformat(since)
        effective_ranges = {
            s: (max(s_start, since_date), s_end)
            for s, (s_start, s_end) in effective_ranges.items()
        }

    print(f"\nTemporadas a procesar: {seasons}")
    if dry_run:
        print("[DRY RUN — no se realizarán cambios en la DB]")

    total_inserted = 0
    total_errors   = 0

    for season in seasons:
        if season not in effective_ranges:
            logger.warning(f"Temporada desconocida: {season}")
            continue
        stats = populate_season(engine, espn_schema, season, dry_run=dry_run,
                                season_ranges=effective_ranges)
        total_inserted += stats["inserted"]
        total_errors   += stats["errors"]

    print("\n" + "=" * 60)
    print(f"RESUMEN FINAL: {total_inserted} partidos insertados, {total_errors} errores")
    if not dry_run and total_inserted > 0:
        print("Recuerda re-ejecutar build_features.py y recover_missing_scores.py.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pobla espn.games con todos los partidos")
    parser.add_argument("--audit-only", action="store_true", help="Solo audita, no inserta")
    parser.add_argument("--dry-run",    action="store_true", help="Muestra qué insertaría, sin cambios")
    parser.add_argument("--since",      default=None,        help="Solo desde esta fecha YYYY-MM-DD")
    parser.add_argument("--season",     default=None,        help="Solo esta temporada: 2023-24 | 2024-25 | 2025-26")
    args = parser.parse_args()

    seasons = [args.season] if args.season else None

    populate_all_games(
        seasons=seasons,
        since=args.since,
        dry_run=args.dry_run,
        audit_only=args.audit_only,
    )
