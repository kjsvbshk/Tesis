"""
Scraper de boxscores de jugadores faltantes (todas las temporadas).

Busca juegos con mapping ESPN→NBA que no tengan boxscores en nba_player_boxscores.
Usa NBA.com __NEXT_DATA__ para obtener stats de jugadores.

Uso:
    python scrape_missing_2026_boxscores.py               # scrapea e inserta
    python scrape_missing_2026_boxscores.py --dry-run     # solo muestra cuántos
    python scrape_missing_2026_boxscores.py --limit 10    # procesa solo N juegos
"""

import sys
import time
import argparse
import re
import json
import requests
from pathlib import Path
from datetime import date

from sqlalchemy import create_engine, text
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ML"))
from src.config import db_config

SLEEP = 0.6   # segundos entre requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_int(v) -> int:
    if v is None or v == "": return 0
    try: return int(float(v))
    except: return 0

def safe_float(v) -> float:
    if v is None or v == "": return 0.0
    try: return float(v)
    except: return 0.0

def minutes_to_str(v) -> str:
    if v is None: return "0:00"
    return str(v)


def fetch_boxscore(nba_id: str) -> dict | None:
    """Fetches player boxscore from NBA.com __NEXT_DATA__. Returns raw game dict or None."""
    url = f"https://www.nba.com/game/{nba_id}/box-score"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            resp.text, re.DOTALL
        )
        if not m:
            logger.warning(f"No __NEXT_DATA__ for {nba_id}")
            return None
        nd = json.loads(m.group(1))
        game = nd.get("props", {}).get("pageProps", {}).get("game", {})
        if not game:
            logger.warning(f"Empty game data for {nba_id}")
            return None
        return game
    except Exception as e:
        logger.warning(f"Error fetching {nba_id}: {e}")
        return None


def parse_players(game: dict, game_id: str, game_date) -> list[dict]:
    """Converts NBA.com game dict → list of rows for nba_player_boxscores."""
    rows = []
    for side in ("homeTeam", "awayTeam"):
        team = game.get(side, {})
        tricode = team.get("teamTricode", "")
        for p in team.get("players", []):
            stats = p.get("statistics") or {}
            # minutes is in 'PT12M30.00S' ISO format or 'MM:SS'
            mins_raw = str(stats.get("minutes", "PT0M0.00S") or "PT0M0.00S")
            if mins_raw.startswith("PT"):
                import re as _re
                mm = _re.match(r"PT(\d+)M([\d.]+)S", mins_raw)
                mins_str = f"{mm.group(1)}:{int(float(mm.group(2))):02d}" if mm else "0:00"
            else:
                mins_str = mins_raw if mins_raw else "0:00"

            rows.append({
                "game_id":      game_id,
                "game_date":    game_date,
                "team_tricode": tricode,
                "player_id":    safe_int(p.get("personId")),
                "player_name":  f"{p.get('firstName','')} {p.get('familyName','')}".strip(),
                "position":     p.get("position", "") or "",
                "starter":      str(p.get("starter", "0")) == "1",
                "minutes":      mins_str,
                "pts":          safe_int(stats.get("points")),
                "reb":          safe_int(stats.get("reboundsTotal")),
                "ast":          safe_int(stats.get("assists")),
                "stl":          safe_int(stats.get("steals")),
                "blk":          safe_int(stats.get("blocks")),
                "to_stat":      safe_int(stats.get("turnovers")),
                "pf":           safe_int(stats.get("foulsPersonal")),
                "plus_minus":   safe_int(stats.get("plusMinusPoints")),
                "fgm":          safe_int(stats.get("fieldGoalsMade")),
                "fga":          safe_int(stats.get("fieldGoalsAttempted")),
                "fg_pct":       safe_float(stats.get("fieldGoalsPercentage")),
                "three_pm":     safe_int(stats.get("threePointersMade")),
                "three_pa":     safe_int(stats.get("threePointersAttempted")),
                "three_pct":    safe_float(stats.get("threePointersPercentage")),
                "ftm":          safe_int(stats.get("freeThrowsMade")),
                "fta":          safe_int(stats.get("freeThrowsAttempted")),
                "ft_pct":       safe_float(stats.get("freeThrowsPercentage")),
                "oreb":         safe_int(stats.get("reboundsOffensive")),
                "dreb":         safe_int(stats.get("reboundsDefensive")),
            })
    return rows


def insert_rows(conn, espn_schema: str, rows: list[dict]) -> int:
    inserted = 0
    for r in rows:
        try:
            conn.execute(text(f"""
                INSERT INTO {espn_schema}.nba_player_boxscores
                    (game_id, game_date, team_tricode, player_id, player_name,
                     position, starter, minutes, pts, reb, ast, stl, blk,
                     to_stat, pf, plus_minus, fgm, fga, fg_pct, three_pm, three_pa,
                     three_pct, ftm, fta, ft_pct, oreb, dreb)
                VALUES
                    (:game_id, :game_date, :team_tricode, :player_id, :player_name,
                     :position, :starter, :minutes, :pts, :reb, :ast, :stl, :blk,
                     :to_stat, :pf, :plus_minus, :fgm, :fga, :fg_pct, :three_pm, :three_pa,
                     :three_pct, :ftm, :fta, :ft_pct, :oreb, :dreb)
                ON CONFLICT DO NOTHING
            """), r)
            inserted += 1
        except Exception as e:
            logger.warning(f"  Insert error player {r['player_id']} game {r['game_id']}: {e}")
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False, limit: int | None = None):
    engine = create_engine(db_config.get_database_url(), pool_pre_ping=True)
    espn_schema = db_config.get_schema("espn")

    # Find missing games
    import pandas as pd
    missing = pd.read_sql(text(f"""
        SELECT m.espn_id, m.nba_id::text AS nba_id, g.fecha, g.home_team, g.away_team
        FROM {espn_schema}.game_id_mapping m
        JOIN {espn_schema}.games g ON g.game_id::text = m.espn_id
        WHERE g.home_score > 0
          AND NOT EXISTS (
            SELECT 1 FROM {espn_schema}.nba_player_boxscores b
            WHERE b.game_id::text = m.nba_id::text
          )
        ORDER BY g.fecha
    """), engine)

    print(f"\nMissing player boxscores (all seasons): {len(missing)}")
    if dry_run:
        print("[DRY RUN] No insertions will be made.")
        print(missing[["nba_id", "fecha", "away_team", "home_team"]].to_string(index=False))
        return

    if missing.empty:
        print("Nothing to scrape.")
        return

    if limit:
        missing = missing.head(limit)
        print(f"Processing only first {limit} games.")

    ok = 0
    failed = 0

    for i, row in missing.iterrows():
        nba_id = row["nba_id"]
        fecha = row["fecha"]
        print(f"  [{ok+failed+1}/{len(missing)}] {nba_id}  {row['away_team']} @ {row['home_team']}  {fecha}", end=" ... ")

        game = fetch_boxscore(nba_id)
        if not game:
            print("FAILED (no data)")
            failed += 1
            time.sleep(SLEEP)
            continue

        rows = parse_players(game, nba_id, fecha)
        if not rows:
            print("FAILED (no players)")
            failed += 1
            time.sleep(SLEEP)
            continue

        with engine.begin() as conn:
            n = insert_rows(conn, espn_schema, rows)

        print(f"OK ({len(rows)} rows inserted)")
        ok += 1
        time.sleep(SLEEP)

    print(f"\nDone: {ok} games scraped, {failed} failed.")
    if ok > 0:
        print("Re-run build_features.py to update rolling features.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(dry_run=args.dry_run, limit=args.limit)
