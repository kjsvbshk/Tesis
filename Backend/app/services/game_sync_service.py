"""
GameSyncService — sincroniza espn.games con la API scoreboard de ESPN.

Misma lógica que Scrapping/nba/sync_espn_games.py pero usando la sesión
SQLAlchemy del backend, para poder dispararla desde un endpoint admin
(POST /api/v1/admin/sync-games) o desde un pinger externo.

Tras el upsert invalida los cachés de matches y predictions_upcoming para
que la UI refleje los partidos nuevos de inmediato.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.cache_service import cache_service

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"


class GameSyncService:
    def __init__(self, db: Session):
        """db debe ser la sesión del schema espn (get_espn_db)."""
        self.db = db

    def sync(self, days_back: int = 1, days_forward: int = 7) -> Dict[str, Any]:
        """
        Descarga los partidos del rango [-days_back, +days_forward] desde la
        API de ESPN y hace upsert en espn.games.

        Returns:
            dict con fechas consultadas, partidos sincronizados y errores.
        """
        start = datetime.now() - timedelta(days=days_back)
        dates = [
            (start + timedelta(days=i)).strftime("%Y%m%d")
            for i in range(days_back + days_forward + 1)
        ]

        games: List[Tuple] = []
        fetch_errors: List[str] = []
        for date_str in dates:
            try:
                games.extend(self._fetch_games(date_str))
            except Exception as e:
                fetch_errors.append(f"{date_str}: {e}")

        synced = 0
        if games:
            synced = self._upsert_games(games)
            # Invalidar cachés para que /matches/upcoming y
            # /predict/upcoming recalculen con los partidos nuevos.
            cache_service.invalidate_pattern("matches")
            cache_service.invalidate_pattern("predictions_upcoming")

        return {
            "dates_queried": [dates[0], dates[-1]],
            "games_fetched": len(games),
            "games_synced": synced,
            "fetch_errors": fetch_errors,
            "synced_at": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------

    def _fetch_games(self, date_str: str) -> List[Tuple]:
        """Partidos de una fecha desde la API scoreboard de ESPN."""
        resp = requests.get(
            f"{ESPN_SCOREBOARD_URL}?dates={date_str}&limit=100", timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        games = []
        for event in data.get("events", []):
            try:
                game_id = int(event["id"])
                fecha = event["date"].split("T")[0]

                comps = event["competitions"][0]["competitors"]
                home = next(c for c in comps if c["homeAway"] == "home")
                away = next(c for c in comps if c["homeAway"] == "away")

                def _score(c):
                    try:
                        return float(c.get("score")) if c.get("score") is not None else None
                    except (TypeError, ValueError):
                        return None

                games.append((
                    game_id,
                    fecha,
                    home["team"]["displayName"],
                    away["team"]["displayName"],
                    _score(home),
                    _score(away),
                ))
            except (KeyError, StopIteration, ValueError):
                continue
        return games

    def _upsert_games(self, games: List[Tuple]) -> int:
        """Upsert en espn.games. Solo toca columnas básicas (no pisa stats del ETL)."""
        upsert = text("""
            INSERT INTO espn.games (game_id, fecha, home_team, away_team, home_score, away_score)
            VALUES (:game_id, :fecha, :home_team, :away_team, :home_score, :away_score)
            ON CONFLICT (game_id) DO UPDATE SET
                fecha = EXCLUDED.fecha,
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team,
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score
        """)
        params = [
            {
                "game_id": g[0], "fecha": g[1],
                "home_team": g[2], "away_team": g[3],
                "home_score": g[4], "away_score": g[5],
            }
            for g in games
        ]
        self.db.execute(upsert, params)
        self.db.commit()
        return len(params)
