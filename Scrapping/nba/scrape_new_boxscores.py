"""
Scrape boxscores para juegos recientes sin mapping.

A diferencia de scrape_missing_2026_boxscores.py (que requiere mappings),
este script obtiene NBA game_ids directamente del scoreboard de NBA.com
para fechas especificas, scrape boxscores, y crea los mappings.

Flujo:
  1. Consulta ESPN games con score>0 pero sin mapping
  2. Para cada fecha, obtiene NBA game_ids del scoreboard CDN
  3. Match por equipos (tricodes)
  4. Scrape boxscore e inserta en nba_player_boxscores
  5. Crea mapping en game_id_mapping

Uso:
    cd Scrapping/nba
    python scrape_new_boxscores.py
    python scrape_new_boxscores.py --dry-run
"""

import sys
import time
import argparse
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ML"))
from src.config import db_config

SLEEP = 0.6
HEADERS_NBA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ESPN team name -> NBA tricode
TEAM_TO_TRICODE = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "LA Clippers": "LAC",
    "Memphis Grizzlies": "MEM", "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}


def safe_int(v) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return 0


def safe_float(v) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def get_unmapped_scored_games(engine, schema):
    """ESPN games con score>0, fecha pasada, sin mapping."""
    df = pd.read_sql(text(f"""
        SELECT g.game_id::text AS espn_id, g.fecha, g.home_team, g.away_team,
               g.home_score, g.away_score
        FROM {schema}.games g
        LEFT JOIN {schema}.game_id_mapping m ON g.game_id::text = m.espn_id
        WHERE m.espn_id IS NULL
          AND g.home_score > 0
          AND g.fecha < CURRENT_DATE
        ORDER BY g.fecha
    """), engine)
    return df


_CDN_SCHEDULE_CACHE = None


def load_cdn_schedule() -> dict:
    """Load full season schedule from NBA CDN. Returns {date_str: [game_dicts]}."""
    global _CDN_SCHEDULE_CACHE
    if _CDN_SCHEDULE_CACHE is not None:
        return _CDN_SCHEDULE_CACHE

    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nba.com/"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    schedule = {}
    for d in data.get("leagueSchedule", {}).get("gameDates", []):
        # gameDate format: "03/18/2026 00:00:00"
        raw_date = d.get("gameDate", "")
        try:
            dt = datetime.strptime(raw_date.split(" ")[0], "%m/%d/%Y")
            date_key = dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

        games = []
        for g in d.get("games", []):
            ht = g.get("homeTeam", {}).get("teamTricode", "")
            at = g.get("awayTeam", {}).get("teamTricode", "")
            gid = g.get("gameId", "")
            if gid and ht and at:
                games.append({
                    "game_id": gid,
                    "home_tricode": ht,
                    "away_tricode": at,
                })
        if games:
            schedule[date_key] = games

    _CDN_SCHEDULE_CACHE = schedule
    logger.info(f"CDN schedule loaded: {len(schedule)} dates")
    return schedule


def fetch_nba_games_for_date(date_str: str) -> list[dict]:
    """Get NBA games for a date from CDN schedule cache."""
    schedule = load_cdn_schedule()
    return schedule.get(date_str, [])


def fetch_boxscore(nba_id: str) -> dict | None:
    """Fetch player boxscore from NBA.com."""
    url = f"https://www.nba.com/game/{nba_id}/box-score"
    try:
        resp = requests.get(url, headers=HEADERS_NBA, timeout=30)
        resp.raise_for_status()
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            resp.text, re.DOTALL,
        )
        if not m:
            return None
        nd = json.loads(m.group(1))
        game = nd.get("props", {}).get("pageProps", {}).get("game", {})
        return game if game else None
    except Exception as e:
        logger.warning(f"Error fetching boxscore {nba_id}: {e}")
        return None


def parse_players(game: dict, game_id: str, game_date) -> list[dict]:
    """Convert NBA.com game dict to list of player boxscore rows."""
    rows = []
    for side in ("homeTeam", "awayTeam"):
        team = game.get(side, {})
        tricode = team.get("teamTricode", "")
        for p in team.get("players", []):
            stats = p.get("statistics") or {}
            mins_raw = str(stats.get("minutes", "PT0M0.00S") or "PT0M0.00S")
            if mins_raw.startswith("PT"):
                mm = re.match(r"PT(\d+)M([\d.]+)S", mins_raw)
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


def insert_boxscore_rows(conn, schema, rows):
    inserted = 0
    for r in rows:
        try:
            conn.execute(text(f"""
                INSERT INTO {schema}.nba_player_boxscores
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
            logger.warning(f"  Insert error: {e}")
    return inserted


def insert_mapping(conn, schema, espn_id, nba_id, season=None):
    try:
        conn.execute(text(f"""
            INSERT INTO {schema}.game_id_mapping (espn_id, nba_id, season)
            VALUES (:espn_id, :nba_id, :season)
            ON CONFLICT DO NOTHING
        """), {"espn_id": espn_id, "nba_id": nba_id, "season": season})
        return True
    except Exception as e:
        logger.warning(f"  Mapping insert error: {e}")
        return False


def run(dry_run=False, limit=None):
    engine = create_engine(db_config.get_database_url(), pool_pre_ping=True)
    schema = db_config.get_schema("espn")

    unmapped = get_unmapped_scored_games(engine, schema)
    print(f"\nJuegos jugados sin mapping: {len(unmapped)}")

    if unmapped.empty:
        print("Todos los juegos jugados tienen mapping.")
        return

    # Agrupar por fecha
    dates_games = defaultdict(list)
    for _, row in unmapped.iterrows():
        fecha_str = str(row["fecha"])[:10]
        home_tc = TEAM_TO_TRICODE.get(row["home_team"], row["home_team"][:3].upper())
        away_tc = TEAM_TO_TRICODE.get(row["away_team"], row["away_team"][:3].upper())
        dates_games[fecha_str].append({
            "espn_id": row["espn_id"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_tc": home_tc,
            "away_tc": away_tc,
        })

    print(f"Fechas a consultar: {len(dates_games)}")

    if limit:
        # Limit to first N dates
        dates_to_process = dict(list(dates_games.items())[:limit])
    else:
        dates_to_process = dates_games

    total_mapped = 0
    total_boxscores = 0
    total_failed = 0

    for date_str, espn_games in sorted(dates_to_process.items()):
        print(f"\n--- {date_str} ({len(espn_games)} juegos ESPN) ---")

        # ESPN dates can be 1 day ahead of NBA CDN dates (timezone offset)
        # Try exact date first, then date - 1
        prev_date = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        nba_games = fetch_nba_games_for_date(date_str)
        nba_games_prev = fetch_nba_games_for_date(prev_date)
        all_nba = nba_games + nba_games_prev

        if not all_nba:
            print(f"  No se pudieron obtener juegos NBA para {date_str}")
            total_failed += len(espn_games)
            time.sleep(SLEEP)
            continue

        print(f"  NBA games encontrados: {len(nba_games)} ({date_str}) + {len(nba_games_prev)} ({prev_date})")

        # Match por tricodes (exact date priority, then day before)
        for eg in espn_games:
            matched_nba = None
            for ng in nba_games:
                if ng["home_tricode"] == eg["home_tc"] and ng["away_tricode"] == eg["away_tc"]:
                    matched_nba = ng
                    break
            if not matched_nba:
                for ng in nba_games_prev:
                    if ng["home_tricode"] == eg["home_tc"] and ng["away_tricode"] == eg["away_tc"]:
                        matched_nba = ng
                        break

            if not matched_nba:
                print(f"  {eg['away_tc']} @ {eg['home_tc']}: NO MATCH en NBA.com")
                total_failed += 1
                continue

            nba_id = matched_nba["game_id"]
            print(f"  {eg['away_tc']} @ {eg['home_tc']}: NBA ID = {nba_id}", end=" ")

            if dry_run:
                print("[DRY RUN]")
                total_mapped += 1
                continue

            # Scrape boxscore
            game_data = fetch_boxscore(nba_id)
            if not game_data:
                print("BOXSCORE FAILED")
                total_failed += 1
                time.sleep(SLEEP)
                continue

            players = parse_players(game_data, nba_id, date_str)
            if not players:
                print("NO PLAYERS")
                total_failed += 1
                time.sleep(SLEEP)
                continue

            with engine.begin() as conn:
                n_ins = insert_boxscore_rows(conn, schema, players)
                # Derive NBA season from game date (e.g. 2025-10 -> "2025-26", 2026-03 -> "2025-26")
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                season_start = dt.year if dt.month >= 10 else dt.year - 1
                season_label = f"{season_start}-{str(season_start+1)[-2:]}"
                mapped = insert_mapping(conn, schema, eg["espn_id"], nba_id, season=season_label)

            print(f"OK ({n_ins} players, mapping={'OK' if mapped else 'SKIP'})")
            total_mapped += 1
            total_boxscores += n_ins
            time.sleep(SLEEP)

        time.sleep(SLEEP)

    print(f"\n{'='*50}")
    print(f"Resumen:")
    print(f"  Juegos mapeados + scrapeados: {total_mapped}")
    print(f"  Player rows insertados:       {total_boxscores}")
    print(f"  Fallidos:                      {total_failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape boxscores para juegos sin mapping")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Limitar a N fechas")
    args = parser.parse_args()
    run(dry_run=args.dry_run, limit=args.limit)
