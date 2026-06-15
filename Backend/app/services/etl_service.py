"""
ETL Service — sincroniza partidos NBA desde la ESPN Scoreboard/Summary API.

Flujo por fecha:
  1. GET scoreboard?dates=YYYYMMDD  → lista de game_ids
  2. GET summary?event=<id>         → home_team, away_team, scores, estado
  3. INSERT ... ON CONFLICT(game_id) DO UPDATE scores si el partido ya existe
     y ahora tiene scores reales.

No depende de pandas ni loguru — solo stdlib + requests + sqlalchemy.
"""

from __future__ import annotations

import time
import logging
from datetime import date, timedelta
from typing import Optional

import requests
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_SUMMARY    = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HAW-thesis-scraper/1.0)",
    "Accept":     "application/json",
}
_SLEEP = 0.35   # segundos entre requests a ESPN


# ---------------------------------------------------------------------------
# ESPN API helpers
# ---------------------------------------------------------------------------

def _fetch_game_ids(day: date) -> list[str]:
    """Devuelve los game_ids ESPN para la fecha dada."""
    try:
        resp = requests.get(
            ESPN_SCOREBOARD,
            params={"dates": day.strftime("%Y%m%d"), "limit": 20},
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"[ETL] scoreboard {day}: {exc}")
        return []

    return [str(ev["id"]) for ev in data.get("events", []) if ev.get("id")]


def _fetch_summary(game_id: str) -> Optional[dict]:
    """
    Devuelve un dict con los datos del partido o None si falla.
    Keys: game_id, fecha, home_team, away_team, home_score, away_score,
          completed, game_type.
    """
    try:
        resp = requests.get(
            ESPN_SUMMARY,
            params={"event": game_id},
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"[ETL] summary {game_id}: {exc}")
        return None

    try:
        header = data["header"]
        comp   = header["competitions"][0]
        comps  = comp["competitors"]

        home = next(c for c in comps if c["homeAway"] == "home")
        away = next(c for c in comps if c["homeAway"] == "away")

        status_obj = comp.get("status", {}).get("type", {})
        completed  = status_obj.get("completed", False)

        home_score = int(home.get("score") or 0)
        away_score = int(away.get("score") or 0)

        # Fecha del partido
        fecha_raw = comp.get("date") or header.get("gameDate") or ""
        if fecha_raw:
            from datetime import datetime
            try:
                fecha = datetime.fromisoformat(fecha_raw.replace("Z", "+00:00")).date()
            except ValueError:
                fecha = datetime.strptime(fecha_raw[:10], "%Y-%m-%d").date()
        else:
            fecha = None

        # Tipo de partido
        season_type = header.get("season", {}).get("type", 2)
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
    except (KeyError, StopIteration, ValueError, TypeError) as exc:
        logger.debug(f"[ETL] parse summary {game_id}: {exc}")
        return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_existing_ids(db: Session) -> set[str]:
    rows = db.execute(text("SELECT game_id::text FROM espn.games")).fetchall()
    return {r[0] for r in rows}


def _upsert_game(db: Session, g: dict) -> str:
    """
    Inserta o actualiza un partido.
    - Si es nuevo → INSERT.
    - Si existe y el partido está completado → actualiza scores.
    Retorna 'inserted' | 'updated' | 'skipped'.
    """
    home_win = None
    if g["completed"] and g["home_score"] > 0:
        home_win = 1 if g["home_score"] > g["away_score"] else 0

    hs = g["home_score"] if g["completed"] else 0
    as_ = g["away_score"] if g["completed"] else 0

    result = db.execute(text("""
        INSERT INTO espn.games
            (game_id, fecha, home_team, away_team, home_score, away_score, home_win, game_type)
        VALUES
            (:gid, :fecha, :ht, :at, :hs, :as_, :hw, :gt)
        ON CONFLICT (game_id) DO UPDATE
            SET home_score = CASE
                    WHEN espn.games.home_score = 0 AND EXCLUDED.home_score > 0
                    THEN EXCLUDED.home_score ELSE espn.games.home_score END,
                away_score = CASE
                    WHEN espn.games.away_score = 0 AND EXCLUDED.away_score > 0
                    THEN EXCLUDED.away_score ELSE espn.games.away_score END,
                home_win = CASE
                    WHEN espn.games.home_win IS NULL AND EXCLUDED.home_win IS NOT NULL
                    THEN EXCLUDED.home_win ELSE espn.games.home_win END
        RETURNING
            (xmax = 0) AS was_inserted,
            home_score,
            away_score
    """), {
        "gid":  g["game_id"],
        "fecha": g["fecha"],
        "ht":   g["home_team"],
        "at":   g["away_team"],
        "hs":   hs,
        "as_":  as_,
        "hw":   home_win,
        "gt":   g["game_type"],
    })

    row = result.fetchone()
    if row is None:
        return "skipped"
    was_inserted = row[0]
    return "inserted" if was_inserted else "updated"


# ---------------------------------------------------------------------------
# Punto de entrada público
# ---------------------------------------------------------------------------

def sync_games(
    db: Session,
    date_from: date,
    date_to: date,
    max_days: int = 30,
) -> dict:
    """
    Sincroniza partidos NBA en el rango [date_from, date_to] desde ESPN.

    Parámetros:
        db         — sesión de SQLAlchemy apuntando al schema espn (espn_engine).
        date_from  — primer día a sincronizar.
        date_to    — último día a sincronizar (inclusive).
        max_days   — límite de seguridad para evitar rangos enormes.

    Retorna dict con:
        dates_processed, games_found, inserted, updated, skipped, errors,
        error_details (lista de strings).
    """
    span = (date_to - date_from).days + 1
    if span > max_days:
        raise ValueError(
            f"Rango solicitado ({span} días) supera el máximo permitido ({max_days} días)."
        )

    stats = {
        "dates_processed": 0,
        "games_found":     0,
        "inserted":        0,
        "updated":         0,
        "skipped":         0,
        "errors":          0,
        "error_details":   [],
    }

    current = date_from
    while current <= date_to:
        logger.info(f"[ETL] Procesando {current} ...")
        game_ids = _fetch_game_ids(current)
        stats["games_found"] += len(game_ids)
        stats["dates_processed"] += 1

        for gid in game_ids:
            try:
                summary = _fetch_summary(gid)
                time.sleep(_SLEEP)
                if summary is None:
                    stats["errors"] += 1
                    stats["error_details"].append(f"{gid}: no summary")
                    continue

                action = _upsert_game(db, summary)
                stats[action] += 1

            except Exception as exc:
                logger.error(f"[ETL] game {gid}: {exc}")
                stats["errors"] += 1
                stats["error_details"].append(f"{gid}: {exc}")
                db.rollback()
                continue

        db.commit()
        current += timedelta(days=1)
        time.sleep(_SLEEP)

    logger.info(f"[ETL] Sync completo: {stats}")
    return stats
