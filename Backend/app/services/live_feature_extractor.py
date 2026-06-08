"""
LiveFeatureExtractor — calcula features en tiempo real para partidos futuros.

Para partidos históricos existe una fila en ml.ml_ready_games con features
pre-calculadas. Para partidos FUTUROS (score = 0, sin resultado) no hay fila,
por lo que hay que reconstruir el vector de features desde los últimos datos
de cada equipo disponibles en la DB.

Estrategia:
  1. Para cada equipo, buscar su último partido jugado en ml_ready_games.
  2. Extraer los rolling features de ese partido (ppg_last5, elo, streak, etc.)
     ajustando según si el equipo era local o visitante.
  3. Calcular rest_days desde ese último partido hasta la fecha del partido futuro.
  4. Calcular diferenciales (home - away) exactamente como train.py.
  5. Buscar odds en espn.game_odds si existen para ese partido.

El resultado es un ndarray (1, N_FEATURES) compatible con el modelo activo.
"""

from __future__ import annotations

import numpy as np
from datetime import date, datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.feature_extractor import FEATURE_SETS, ODDS_FEATURES


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class LiveFeaturesError(Exception):
    """No se pueden computar features en vivo para este partido."""


# ---------------------------------------------------------------------------
# LiveFeatureExtractor
# ---------------------------------------------------------------------------

class LiveFeatureExtractor:
    """
    Extrae features para partidos futuros consultando los últimos datos
    disponibles en ml.ml_ready_games y espn.game_odds.

    Args:
        db: SQLAlchemy Session apuntando al schema espn/ml de Neon.
    """

    ML_SCHEMA  = "ml"
    ESPN_SCHEMA = "espn"

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def build_feature_vector(
        self,
        home_team: str,
        away_team: str,
        game_date: date,
        feature_set: str = "v2",
        game_id: Optional[int] = None,
    ) -> np.ndarray:
        """
        Construye el vector X (1, N) para el modelo a partir de los últimos
        datos disponibles de cada equipo.

        Args:
            home_team:   nombre del equipo local (ej. "San Antonio Spurs")
            away_team:   nombre del equipo visitante (ej. "New York Knicks")
            game_date:   fecha del partido futuro
            feature_set: "v1" (21), "v2" (33) o "v2_odds" (35)
            game_id:     ESPN game_id (opcional, para buscar odds específicas)

        Returns:
            ndarray shape (1, N)
        """
        home = self._get_team_latest(home_team, game_date)
        away = self._get_team_latest(away_team, game_date)

        if home is None:
            raise LiveFeaturesError(
                f"No hay datos históricos en ml_ready_games para '{home_team}'. "
                "El equipo no ha jugado partidos previos en la DB."
            )
        if away is None:
            raise LiveFeaturesError(
                f"No hay datos históricos en ml_ready_games para '{away_team}'. "
                "El equipo no ha jugado partidos previos en la DB."
            )

        # Injuries
        home_inj = self._count_injuries(home_team)
        away_inj = self._count_injuries(away_team)

        # H2H
        h2h = self._get_h2h(home_team, away_team)

        # Odds implícitas
        imp_home, imp_away = self._get_implied_probs(game_id, home_team, away_team)

        features = self._build_dict(home, away, home_inj, away_inj, h2h, imp_home, imp_away)

        cols = FEATURE_SETS.get(feature_set)
        if cols is None:
            raise LiveFeaturesError(f"feature_set desconocido: {feature_set}")

        row = [float(features.get(col, np.nan)) for col in cols]
        return np.array([row], dtype=float)

    def get_features_summary(
        self,
        home_team: str,
        away_team: str,
        game_date: date,
        feature_set: str = "v2",
        game_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Devuelve el dict de features para auditoría (mismo formato que FeatureExtractor)."""
        home = self._get_team_latest(home_team, game_date)
        away = self._get_team_latest(away_team, game_date)
        home_inj = self._count_injuries(home_team)
        away_inj = self._count_injuries(away_team)
        h2h = self._get_h2h(home_team, away_team)
        imp_home, imp_away = self._get_implied_probs(game_id, home_team, away_team)

        features = self._build_dict(home, away, home_inj, away_inj, h2h, imp_home, imp_away)
        cols = FEATURE_SETS.get(feature_set, [])
        used = {col: features.get(col) for col in cols}
        return {
            "feature_set": feature_set,
            "n_features": len(cols),
            "values": used,
            "missing_count": sum(1 for v in used.values() if v is None),
            "source": "live",
            "home_last_game": str(home.get("last_game_date")) if home else None,
            "away_last_game": str(away.get("last_game_date")) if away else None,
        }

    # ------------------------------------------------------------------
    # Últimos datos por equipo
    # ------------------------------------------------------------------

    def _get_team_latest(self, team: str, game_date: date) -> Optional[Dict]:
        """
        Busca el último partido jugado por el equipo y extrae sus rolling
        features ajustando home/away.
        """
        query = text(f"""
            SELECT
                fecha,
                home_team,
                away_team,
                CASE WHEN home_team = :team THEN home_ppg_last5     ELSE away_ppg_last5     END AS ppg_last5,
                CASE WHEN home_team = :team THEN home_net_rating_last10 ELSE away_net_rating_last10 END AS net_rating_last10,
                CASE WHEN home_team = :team THEN home_pace_rolling   ELSE away_pace_rolling   END AS pace_rolling,
                CASE WHEN home_team = :team THEN home_off_rating_rolling ELSE away_off_rating_rolling END AS off_rating_rolling,
                CASE WHEN home_team = :team THEN home_def_rating_rolling ELSE away_def_rating_rolling END AS def_rating_rolling,
                CASE WHEN home_team = :team THEN home_reb_rolling    ELSE away_reb_rolling    END AS reb_rolling,
                CASE WHEN home_team = :team THEN home_ast_rolling    ELSE away_ast_rolling    END AS ast_rolling,
                CASE WHEN home_team = :team THEN home_tov_rolling    ELSE away_tov_rolling    END AS tov_rolling,
                CASE WHEN home_team = :team THEN home_win_rate_last10 ELSE away_win_rate_last10 END AS win_rate_last10,
                CASE WHEN home_team = :team THEN home_efg_pct_rolling ELSE away_efg_pct_rolling END AS efg_pct_rolling,
                CASE WHEN home_team = :team THEN home_tov_rate_rolling ELSE away_tov_rate_rolling END AS tov_rate_rolling,
                CASE WHEN home_team = :team THEN home_oreb_pct_rolling ELSE away_oreb_pct_rolling END AS oreb_pct_rolling,
                CASE WHEN home_team = :team THEN home_dreb_pct_rolling ELSE away_dreb_pct_rolling END AS dreb_pct_rolling,
                CASE WHEN home_team = :team THEN home_elo            ELSE away_elo            END AS elo,
                CASE WHEN home_team = :team THEN home_streak         ELSE away_streak         END AS streak,
                CASE WHEN home_team = :team THEN home_home_win_rate  ELSE away_away_win_rate  END AS split_win_rate,
                CASE WHEN home_team = :team THEN home_rest_days      ELSE away_rest_days      END AS last_rest_days,
                CASE WHEN home_team = :team THEN home_avg_margin_rolling ELSE away_avg_margin_rolling END AS avg_margin_rolling,
                CASE WHEN home_team = :team THEN home_player_top3_pts ELSE away_player_top3_pts END AS player_top3_pts,
                CASE WHEN home_team = :team THEN home_player_top3_eff ELSE away_player_top3_eff END AS player_top3_eff
            FROM {self.ML_SCHEMA}.ml_ready_games
            WHERE (home_team = :team OR away_team = :team)
              AND home_win IS NOT NULL
              AND (home_score > 0 OR away_score > 0)
              AND fecha < :game_date
            ORDER BY fecha DESC
            LIMIT 1
        """)
        row = self.db.execute(query, {"team": team, "game_date": str(game_date)}).mappings().first()
        if row is None:
            return None

        result = dict(row)
        result["last_game_date"] = row["fecha"]

        # Rest days desde su último partido hasta el partido futuro
        last_date = row["fecha"]
        if isinstance(last_date, str):
            last_date = datetime.strptime(last_date, "%Y-%m-%d").date()
        if isinstance(game_date, str):
            game_date = datetime.strptime(game_date, "%Y-%m-%d").date()
        result["rest_days"] = (game_date - last_date).days
        result["b2b"] = result["rest_days"] == 1

        return result

    # ------------------------------------------------------------------
    # Lesiones
    # ------------------------------------------------------------------

    def _count_injuries(self, team: str) -> int:
        """Cuenta lesiones activas del equipo en espn.injuries."""
        NICKNAME_MAP = {
            "Atlanta Hawks": "Hawks", "Boston Celtics": "Celtics",
            "Brooklyn Nets": "Nets", "Charlotte Hornets": "Hornets",
            "Chicago Bulls": "Bulls", "Cleveland Cavaliers": "Cavaliers",
            "Dallas Mavericks": "Mavericks", "Denver Nuggets": "Nuggets",
            "Detroit Pistons": "Pistons", "Golden State Warriors": "Warriors",
            "Houston Rockets": "Rockets", "Indiana Pacers": "Pacers",
            "Los Angeles Clippers": "Clippers", "LA Clippers": "Clippers",
            "Los Angeles Lakers": "Lakers", "Memphis Grizzlies": "Grizzlies",
            "Miami Heat": "Heat", "Milwaukee Bucks": "Bucks",
            "Minnesota Timberwolves": "Timberwolves",
            "New Orleans Pelicans": "Pelicans", "New York Knicks": "Knicks",
            "Oklahoma City Thunder": "Thunder", "Orlando Magic": "Magic",
            "Philadelphia 76ers": "76ers", "Phoenix Suns": "Suns",
            "Portland Trail Blazers": "Trail Blazers",
            "Sacramento Kings": "Kings", "San Antonio Spurs": "Spurs",
            "Toronto Raptors": "Raptors", "Utah Jazz": "Jazz",
            "Washington Wizards": "Wizards",
        }
        nickname = NICKNAME_MAP.get(team, team)
        try:
            result = self.db.execute(
                text(f"SELECT COUNT(*) FROM {self.ESPN_SCHEMA}.injuries WHERE team = :t"),
                {"t": nickname}
            ).scalar()
            return int(result or 0)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # H2H
    # ------------------------------------------------------------------

    def _get_h2h(self, home_team: str, away_team: str, n: int = 5) -> float:
        """Fracción de victorias del home_team en los últimos n enfrentamientos."""
        query = text(f"""
            SELECT home_win
            FROM {self.ML_SCHEMA}.ml_ready_games
            WHERE ((home_team = :ht AND away_team = :at)
                OR (home_team = :at AND away_team = :ht))
              AND home_win IS NOT NULL
            ORDER BY fecha DESC
            LIMIT :n
        """)
        rows = self.db.execute(query, {"ht": home_team, "at": away_team, "n": n}).fetchall()
        if not rows:
            return 0.5
        wins = sum(
            1 for r in rows
            if (r[0] is True or r[0] == 1)
        )
        return round(wins / len(rows), 4)

    # ------------------------------------------------------------------
    # Odds implícitas
    # ------------------------------------------------------------------

    def _get_implied_probs(
        self, game_id: Optional[int], home_team: str, away_team: str
    ):
        """Busca implied_prob en ml_ready_games o en espn.game_odds."""
        # 1. Si el game_id ya existe en ml_ready_games con odds
        if game_id:
            try:
                row = self.db.execute(text(f"""
                    SELECT implied_prob_home, implied_prob_away
                    FROM {self.ML_SCHEMA}.ml_ready_games
                    WHERE game_id = :gid
                """), {"gid": game_id}).mappings().first()
                if row and row["implied_prob_home"] is not None:
                    return float(row["implied_prob_home"]), float(row["implied_prob_away"])
            except Exception:
                pass

        # 2. Buscar en espn.game_odds para cualquier game_id que coincida con estos equipos
        try:
            row = self.db.execute(text(f"""
                SELECT
                    AVG(CASE WHEN go.odds_type = 'moneyline_home' THEN go.odds_value END) AS ml_home,
                    AVG(CASE WHEN go.odds_type = 'moneyline_away' THEN go.odds_value END) AS ml_away
                FROM {self.ESPN_SCHEMA}.game_odds go
                JOIN {self.ESPN_SCHEMA}.odds_event_game_map m ON go.game_id = m.game_id
                JOIN {self.ESPN_SCHEMA}.odds o ON o.game_id = m.odds_id
                WHERE go.odds_type IN ('moneyline_home', 'moneyline_away')
                  AND o.home_team = :ht AND o.away_team = :at
                GROUP BY go.game_id
                LIMIT 1
            """), {"ht": home_team, "at": away_team}).mappings().first()

            if row and row["ml_home"] and row["ml_away"]:
                ml_h, ml_a = float(row["ml_home"]), float(row["ml_away"])
                # Convertir decimal → implied prob normalizada
                raw_h = 1.0 / ml_h if ml_h > 0 else 0.5
                raw_a = 1.0 / ml_a if ml_a > 0 else 0.5
                total = raw_h + raw_a
                return round(raw_h / total, 4), round(raw_a / total, 4)
        except Exception:
            pass

        return None, None

    # ------------------------------------------------------------------
    # Construcción del dict de features
    # ------------------------------------------------------------------

    def _build_dict(
        self, home: Dict, away: Dict,
        home_inj: int, away_inj: int,
        h2h: float,
        imp_home: Optional[float],
        imp_away: Optional[float],
    ) -> Dict[str, Any]:
        """
        Construye el dict de features usando la misma lógica que build_features.py
        y la misma convención de nombres que train.py.
        """
        def g(d, key):
            """Obtiene valor del dict o NaN si es None."""
            v = d.get(key)
            return float(v) if v is not None else np.nan

        f = {}

        # ── Individuales ──────────────────────────────────────────────
        f["home_ppg_last5"]       = g(home, "ppg_last5")
        f["away_ppg_last5"]       = g(away, "ppg_last5")
        f["home_rest_days"]       = float(home.get("rest_days", 3))
        f["away_rest_days"]       = float(away.get("rest_days", 3))
        f["home_b2b"]             = float(bool(home.get("b2b", False)))
        f["away_b2b"]             = float(bool(away.get("b2b", False)))
        f["home_injuries_count"]  = float(home_inj)
        f["away_injuries_count"]  = float(away_inj)
        f["home_win_rate_last10"] = g(home, "win_rate_last10")
        f["away_win_rate_last10"] = g(away, "win_rate_last10")
        f["home_elo"]             = g(home, "elo")
        f["away_elo"]             = g(away, "elo")
        f["home_streak"]          = g(home, "streak")
        f["away_streak"]          = g(away, "streak")
        f["h2h_home_advantage"]   = h2h

        # ── Diferenciales ─────────────────────────────────────────────
        f["ppg_diff"]              = g(home, "ppg_last5")      - g(away, "ppg_last5")
        f["net_rating_diff_rolling"] = g(home, "net_rating_last10") - g(away, "net_rating_last10")
        f["rest_days_diff"]        = f["home_rest_days"] - f["away_rest_days"]
        f["injuries_diff"]         = float(home_inj) - float(away_inj)
        f["pace_diff"]             = g(home, "pace_rolling")   - g(away, "pace_rolling")
        f["off_rating_diff"]       = g(home, "off_rating_rolling") - g(away, "off_rating_rolling")
        f["def_rating_diff"]       = g(home, "def_rating_rolling") - g(away, "def_rating_rolling")
        f["reb_rolling_diff"]      = g(home, "reb_rolling")    - g(away, "reb_rolling")
        f["ast_rolling_diff"]      = g(home, "ast_rolling")    - g(away, "ast_rolling")
        f["tov_rolling_diff"]      = g(home, "tov_rolling")    - g(away, "tov_rolling")
        f["win_rate_diff"]         = g(home, "win_rate_last10") - g(away, "win_rate_last10")
        f["efg_pct_diff"]          = g(home, "efg_pct_rolling") - g(away, "efg_pct_rolling")
        f["tov_rate_diff"]         = g(home, "tov_rate_rolling") - g(away, "tov_rate_rolling")
        f["oreb_pct_diff"]         = g(home, "oreb_pct_rolling") - g(away, "oreb_pct_rolling")
        f["dreb_pct_diff"]         = g(home, "dreb_pct_rolling") - g(away, "dreb_pct_rolling")
        f["elo_diff"]              = g(home, "elo")    - g(away, "elo")
        f["streak_diff"]           = g(home, "streak") - g(away, "streak")
        f["home_away_split_diff"]  = g(home, "split_win_rate") - g(away, "split_win_rate")

        # ── Odds ──────────────────────────────────────────────────────
        f["implied_prob_home"] = float(imp_home) if imp_home is not None else np.nan
        f["implied_prob_away"] = float(imp_away) if imp_away is not None else np.nan

        # ── V3: Rest flags ─────────────────────────────────────────────
        h_rest = f["home_rest_days"]
        a_rest = f["away_rest_days"]
        f["home_big_rest"]       = 1.0 if h_rest >= 3 else 0.0
        f["away_big_rest"]       = 1.0 if a_rest >= 3 else 0.0
        f["home_optimal_rest"]   = 1.0 if h_rest == 2 else 0.0
        f["away_optimal_rest"]   = 1.0 if a_rest == 2 else 0.0
        f["home_excessive_rest"] = 1.0 if h_rest >= 5 else 0.0
        f["away_excessive_rest"] = 1.0 if a_rest >= 5 else 0.0

        # ── V3: Player star features ───────────────────────────────────
        f["home_avg_margin_rolling"]  = g(home, "avg_margin_rolling")
        f["away_avg_margin_rolling"]  = g(away, "avg_margin_rolling")
        f["home_player_top3_pts"]     = g(home, "player_top3_pts")
        f["away_player_top3_pts"]     = g(away, "player_top3_pts")
        f["home_player_top3_eff"]     = g(home, "player_top3_eff")
        f["away_player_top3_eff"]     = g(away, "player_top3_eff")

        # ── V3: Diferenciales ─────────────────────────────────────────
        f["avg_margin_diff"]           = f["home_avg_margin_rolling"] - f["away_avg_margin_rolling"]
        f["player_top3_pts_advantage"] = f["home_player_top3_pts"]   - f["away_player_top3_pts"]
        f["player_top3_eff_advantage"] = f["home_player_top3_eff"]   - f["away_player_top3_eff"]

        # strength_composite: promedio ponderado ELO + net_rating + win_rate
        elo_d = f.get("elo_diff", 0.0) or 0.0
        nrt_d = f.get("net_rating_diff_rolling", 0.0) or 0.0
        wr_d  = f.get("win_rate_diff", 0.0) or 0.0
        f["strength_composite"] = (
            0.4 * elo_d / 100.0
            + 0.35 * nrt_d / 10.0
            + 0.25 * wr_d
        )

        return f
