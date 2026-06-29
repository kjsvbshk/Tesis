"""
ESPN Odds Sync Service
Fetches odds from the ESPN public API and upserts into espn.game_odds.

ESPN endpoint (no API key required):
  GET https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{event_id}/competitions/{event_id}/odds
"""

import httpx
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Provider name normalization (ESPN name → our stored name)
_PROVIDER_MAP = {
    "DraftKings": "draftkings",
    "FanDuel": "fanduel",
    "BetMGM": "betmgm",
    "BetRivers": "betrivers",
    "MyBookie.ag": "mybookieag",
    "Caesars": "caesars",
    "PointsBet": "pointsbet",
    "bet365": "bet365",
}

ESPN_ODDS_URL = (
    "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
    "/events/{event_id}/competitions/{event_id}/odds"
)


def _american_to_decimal(american: Optional[float]) -> Optional[float]:
    """Convert American moneyline odds to decimal (European) format.
    e.g. -150 → 1.67,  +130 → 2.30
    """
    if american is None:
        return None
    if american > 0:
        return round((american / 100) + 1, 4)
    elif american < 0:
        return round((100 / abs(american)) + 1, 4)
    return None


def _upsert_odd(
    db: Session,
    game_id: int,
    odds_type: str,
    odds_value: Optional[float],
    line_value: Optional[float],
    provider: str,
) -> None:
    """Insert or update a single odds row in espn.game_odds."""
    if odds_value is None and line_value is None:
        return
    db.execute(
        text("""
            INSERT INTO espn.game_odds (game_id, odds_type, odds_value, line_value, provider, snapshot_time)
            VALUES (:game_id, :odds_type, :odds_value, :line_value, :provider, NOW())
            ON CONFLICT DO NOTHING
        """),
        {
            "game_id": game_id,
            "odds_type": odds_type,
            "odds_value": odds_value,
            "line_value": line_value,
            "provider": provider,
        },
    )


def _parse_and_upsert(db: Session, game_id: int, odds_items: list) -> int:
    """Parse ESPN odds response items and upsert into DB. Returns count of rows written."""
    written = 0
    for item in odds_items:
        provider_raw = item.get("provider", {}).get("name", "")
        provider = _PROVIDER_MAP.get(provider_raw, provider_raw.lower().replace(" ", ""))

        home_moneyline = item.get("homeTeamOdds", {}).get("moneyLine")
        away_moneyline = item.get("awayTeamOdds", {}).get("moneyLine")
        over_under_line = item.get("overUnder")  # float, e.g. 224.5

        # Moneyline home
        home_decimal = _american_to_decimal(home_moneyline)
        if home_decimal is not None:
            _upsert_odd(db, game_id, "moneyline_home", home_decimal, None, provider)
            written += 1

        # Moneyline away
        away_decimal = _american_to_decimal(away_moneyline)
        if away_decimal is not None:
            _upsert_odd(db, game_id, "moneyline_away", away_decimal, None, provider)
            written += 1

        # Spread home
        spread_home_val = item.get("homeTeamOdds", {}).get("spreadOdds")
        spread_line_raw = item.get("details", "")  # e.g. "-5.5" or "LAL -5.5"
        spread_line: Optional[float] = None
        try:
            # Extract numeric value from details string like "-5.5" or "LAL -5.5"
            parts = spread_line_raw.replace("+", " +").split()
            for part in reversed(parts):
                spread_line = float(part)
                break
        except (ValueError, AttributeError):
            pass

        spread_home_decimal = _american_to_decimal(spread_home_val)
        if spread_home_decimal is not None or spread_line is not None:
            _upsert_odd(db, game_id, "spread_home", spread_home_decimal, spread_line, provider)
            written += 1

        # Spread away (mirror of spread line)
        spread_away_val = item.get("awayTeamOdds", {}).get("spreadOdds")
        spread_away_decimal = _american_to_decimal(spread_away_val)
        away_spread_line = -spread_line if spread_line is not None else None
        if spread_away_decimal is not None or away_spread_line is not None:
            _upsert_odd(db, game_id, "spread_away", spread_away_decimal, away_spread_line, provider)
            written += 1

        # Over/Under
        if over_under_line is not None:
            # ESPN doesn't return separate over/under odds — use standard -110 → 1.909
            _upsert_odd(db, game_id, "over_under", 1.909, over_under_line, provider)
            written += 1

    return written


async def sync_game_odds(db: Session, espn_game_id: int) -> dict:
    """
    Fetch odds for one game from ESPN and upsert into espn.game_odds.
    Returns a summary dict with counts.
    """
    url = ESPN_ODDS_URL.format(event_id=espn_game_id)
    logger.info(f"Fetching ESPN odds for game {espn_game_id}: {url}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers={"Accept": "application/json"})

    if resp.status_code == 404:
        return {"game_id": espn_game_id, "status": "not_found", "rows_written": 0}

    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    if not items:
        return {"game_id": espn_game_id, "status": "no_odds", "rows_written": 0}

    written = _parse_and_upsert(db, espn_game_id, items)
    db.commit()

    logger.info(f"Synced {written} odds rows for game {espn_game_id}")
    return {"game_id": espn_game_id, "status": "ok", "rows_written": written, "providers": len(items)}


async def sync_bulk_odds(db: Session, espn_game_ids: list[int]) -> dict:
    """
    Sync odds for multiple games. Continues on individual failures.
    """
    results = []
    total_written = 0
    errors = 0

    for gid in espn_game_ids:
        try:
            result = await sync_game_odds(db, gid)
            results.append(result)
            total_written += result.get("rows_written", 0)
        except Exception as e:
            logger.error(f"Failed to sync odds for game {gid}: {e}")
            results.append({"game_id": gid, "status": "error", "error": str(e)})
            errors += 1

    return {
        "total_games": len(espn_game_ids),
        "total_rows_written": total_written,
        "errors": errors,
        "results": results,
    }


async def sync_recent_games_odds(db: Session, days_back: int = 7, days_forward: int = 7) -> dict:
    """
    Auto-sync odds for all games in espn.games within the date window.
    Uses game_id as ESPN event ID (they match in your DB).
    """
    from datetime import date, timedelta

    today = date.today()
    date_from = today - timedelta(days=days_back)
    date_to = today + timedelta(days=days_forward)

    rows = db.execute(
        text("""
            SELECT game_id FROM espn.games
            WHERE fecha BETWEEN :date_from AND :date_to
            ORDER BY fecha
        """),
        {"date_from": date_from, "date_to": date_to},
    ).fetchall()

    game_ids = [int(r[0]) for r in rows]
    logger.info(f"Auto-sync odds for {len(game_ids)} games ({date_from} → {date_to})")

    return await sync_bulk_odds(db, game_ids)
