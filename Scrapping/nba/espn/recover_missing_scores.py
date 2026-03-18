"""
Script de recuperación de scores faltantes usando la ESPN JSON API.

Identifica partidos jugados que tienen score = 0 en la BD,
luego los actualiza usando:
  https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD

La API JSON de ESPN es más estable que el HTML scraping.

Uso:
    python recover_missing_scores.py
    python recover_missing_scores.py --dry-run     # solo muestra qué actualizaría
    python recover_missing_scores.py --since 2026-02-01
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import date, timedelta

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
SLEEP_BETWEEN_REQUESTS = 0.5   # segundos entre llamadas a la API


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_game_summary(game_id: str) -> dict | None:
    """
    Llama al endpoint de resumen de un partido individual.
    Más confiable que el scoreboard (no tiene dependencia de fecha exacta).

    Returns dict con home_score, away_score, completed o None si falla.
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
        logger.debug(f"Error al llamar summary API game {game_id}: {e}")
        return None

    try:
        competition = data["header"]["competitions"][0]
        competitors = competition["competitors"]

        home = next(c for c in competitors if c["homeAway"] == "home")
        away = next(c for c in competitors if c["homeAway"] == "away")

        status = competition.get("status", {}).get("type", {})
        completed = status.get("completed", False)
        if not completed:
            return None   # partido no terminado aún

        home_score = int(home.get("score", 0) or 0)
        away_score = int(away.get("score", 0) or 0)

        if home_score == 0 and away_score == 0:
            return None   # sin datos reales

        return {
            "game_id":    game_id,
            "home_score": home_score,
            "away_score": away_score,
            "home_team":  home["team"].get("displayName", ""),
            "away_team":  away["team"].get("displayName", ""),
        }
    except (KeyError, StopIteration, ValueError, TypeError):
        return None


def get_missing_games(engine, espn_schema: str, since: str) -> pd.DataFrame:
    """Devuelve los partidos jugados sin score desde una fecha."""
    return pd.read_sql(
        text(f"""
            SELECT game_id::text, fecha, home_team, away_team
            FROM {espn_schema}.games
            WHERE (home_score IS NULL OR home_score = 0)
              AND fecha <= CURRENT_DATE
              AND fecha >= :since
            ORDER BY fecha
        """),
        engine,
        params={"since": since},
    )


def update_scores(conn, espn_schema: str, game_id: str, home_score: int, away_score: int):
    """Actualiza scores y home_win en espn.games y ml_ready_games."""
    # home_win es bigint en la BD → pasar 1/0 en lugar de True/False
    home_win_int = 1 if home_score > away_score else 0
    conn.execute(text(f"""
        UPDATE {espn_schema}.games
        SET home_score = :hs,
            away_score = :as_,
            home_win   = :hw
        WHERE game_id::text = :gid
    """), {"hs": home_score, "as_": away_score, "hw": home_win_int, "gid": game_id})

    # También actualiza ml_ready_games (home_win aquí es boolean)
    conn.execute(text(f"""
        UPDATE ml.ml_ready_games
        SET home_score = :hs,
            away_score = :as_,
            home_win   = :hw
        WHERE game_id::text = :gid
    """), {"hs": home_score, "as_": away_score, "hw": bool(home_win_int), "gid": game_id})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def recover_missing_scores(since: str = "2025-10-01", dry_run: bool = False):
    """Recupera scores faltantes para todos los partidos desde `since`."""
    database_url = db_config.get_database_url()
    espn_schema  = db_config.get_schema("espn")
    engine = create_engine(database_url, pool_pre_ping=True)

    # 1. Obtener partidos sin score
    missing = get_missing_games(engine, espn_schema, since)
    logger.info(f"Partidos jugados sin score: {len(missing)}")
    if missing.empty:
        logger.info("No hay partidos pendientes. Nada que recuperar.")
        return

    # 2. Agrupar por fecha
    missing["fecha_str"] = pd.to_datetime(missing["fecha"]).dt.strftime("%Y%m%d")
    dates = missing["fecha_str"].unique()
    logger.info(f"Fechas a consultar: {len(dates)}")

    # 3. Para cada juego, llamar al endpoint summary individual (más confiable que scoreboard)
    updated = 0
    not_found = 0
    still_future = 0

    all_game_ids = missing["game_id"].astype(str).tolist()
    logger.info(f"Consultando ESPN summary API para {len(all_game_ids)} partidos...")

    with engine.begin() as conn:
        for i, gid in enumerate(all_game_ids, 1):
            result = fetch_game_summary(gid)

            if result is not None:
                # Filtrar eventos especiales (All-Star, G-League, etc.) donde los scores son anómalos
                if result["home_score"] < 60 or result["away_score"] < 60:
                    logger.warning(
                        f"  [{i}/{len(all_game_ids)}] game {gid}: score inusual "
                        f"({result['home_score']}-{result['away_score']}) — saltando"
                    )
                    not_found += 1
                    continue

                logger.info(
                    f"  [{i}/{len(all_game_ids)}] game {gid}: "
                    f"{result['home_team']} {result['home_score']} - "
                    f"{result['away_score']} {result['away_team']}"
                    + (" [DRY RUN]" if dry_run else "")
                )
                if not dry_run:
                    update_scores(conn, espn_schema, gid, result["home_score"], result["away_score"])
                updated += 1
            else:
                # Verificar si el partido es futuro (antes de reportar como no encontrado)
                row = missing[missing["game_id"].astype(str) == gid]
                fecha = pd.to_datetime(row["fecha"].values[0]).date() if not row.empty else None
                if fecha and fecha > date.today():
                    still_future += 1
                    logger.debug(f"  [{i}/{len(all_game_ids)}] game {gid} ({fecha}) — partido futuro, OK")
                else:
                    logger.warning(f"  [{i}/{len(all_game_ids)}] game {gid} ({fecha}) — sin datos en ESPN API")
                    not_found += 1

            time.sleep(SLEEP_BETWEEN_REQUESTS)

    logger.info(f"Resumen: {updated} actualizados, {not_found} sin datos en API, {still_future} partidos futuros")
    if not dry_run and updated > 0:
        logger.info("Recuerda re-ejecutar build_features.py para actualizar los rolling features.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recupera scores faltantes via ESPN API")
    parser.add_argument("--since",    default="2025-10-01", help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--dry-run",  action="store_true",  help="Solo muestra, no actualiza")
    args = parser.parse_args()

    recover_missing_scores(since=args.since, dry_run=args.dry_run)
