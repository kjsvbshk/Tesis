"""
Data loader for ML training
Carga datos desde PostgreSQL (Neon) para entrenar modelos
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from typing import Optional, Dict, Any

from src.config import db_config


class DataLoader:
    """Carga datos desde Neon PostgreSQL para entrenamiento"""

    def __init__(self, schema: str = "espn"):
        self.schema = db_config.get_schema(schema)
        self.database_url = db_config.get_database_url()
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
        )

    def load_table(
        self,
        table: str,
        where: str = "",
        params: Optional[Dict[str, Any]] = None,
        order_by: str = "",
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Generic table loader. Accepts raw WHERE fragment and bind params."""
        query = f"SELECT * FROM {self.schema}.{table} WHERE 1=1{where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        with self.engine.connect() as conn:
            if self.schema:
                conn.execute(text(f"SET search_path TO {self.schema}, public"))
                conn.commit()
            return pd.read_sql(text(query), conn, params=params or {})

    # ------------------------------------------------------------------ #
    # Convenience wrappers (kept for backward-compat; delegate to load_table)
    # ------------------------------------------------------------------ #

    def load_games(
        self,
        season_start: Optional[str] = None,
        season_end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        where, params = "", {}
        if season_start:
            where += " AND (game_date >= :season_start OR date >= :season_start)"
            params["season_start"] = season_start
        if season_end:
            where += " AND (game_date <= :season_end OR date <= :season_end)"
            params["season_end"] = season_end
        return self.load_table("games", where, params, "COALESCE(game_date, date, match_date) DESC", limit)

    def load_team_stats(
        self,
        season: Optional[str] = None,
        game_date: Optional[str] = None,
    ) -> pd.DataFrame:
        where, params = "", {}
        if season:
            where += " AND season = :season"
            params["season"] = season
        if game_date:
            where += " AND (game_date = :game_date OR date = :game_date)"
            params["game_date"] = game_date
        return self.load_table("team_stats", where, params, "COALESCE(game_date, date) DESC")

    def load_standings(self, season: Optional[str] = None) -> pd.DataFrame:
        where, params = "", {}
        if season:
            where += " AND season = :season"
            params["season"] = season
        return self.load_table("standings", where, params, "season DESC, wins DESC")

    def load_injuries(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> pd.DataFrame:
        where, params = "", {}
        if date_from:
            where += " AND (injury_date >= :date_from OR date >= :date_from)"
            params["date_from"] = date_from
        if date_to:
            where += " AND (injury_date <= :date_to OR date <= :date_to)"
            params["date_to"] = date_to
        return self.load_table("injuries", where, params, "COALESCE(injury_date, date) DESC")

    def load_odds(self, game_date: Optional[str] = None) -> pd.DataFrame:
        where, params = "", {}
        if game_date:
            where += " AND (game_date = :game_date OR date = :game_date)"
            params["game_date"] = game_date
        return self.load_table("odds", where, params, "COALESCE(game_date, date) DESC")

    # ------------------------------------------------------------------ #
    # Consolidated dataset                                                 #
    # ------------------------------------------------------------------ #

    def load_consolidated_dataset(
        self,
        season_start: Optional[str] = None,
        season_end: Optional[str] = None,
    ) -> pd.DataFrame:
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "..", "Scrapping", "nba", "data", "processed", "nba_full_dataset.csv",
        )

        if os.path.exists(csv_path):
            print(f"Cargando dataset consolidado desde: {csv_path}")
            df = pd.read_csv(csv_path)
            if season_start or season_end:
                date_col = next(
                    (c for c in ("date", "game_date") if c in df.columns), None
                )
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col])
                    if season_start:
                        df = df[df[date_col] >= pd.to_datetime(season_start)]
                    if season_end:
                        df = df[df[date_col] <= pd.to_datetime(season_end)]
            return df

        print(f"CSV consolidado no encontrado en {csv_path}, construyendo desde base de datos...")
        games = self.load_games(season_start=season_start, season_end=season_end)
        if games.empty:
            print("No se encontraron partidos en la base de datos")
        return games

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                if self.schema:
                    conn.execute(text(f"SET search_path TO {self.schema}, public"))
                    conn.commit()
                conn.execute(text("SELECT 1")).fetchone()
            return True
        except Exception as e:
            print(f"Error de conexión: {e}")
            return False


def load_nba_data(
    season_start: Optional[str] = None,
    season_end: Optional[str] = None,
    from_csv: bool = True,
) -> pd.DataFrame:
    loader = DataLoader(schema="espn")
    if not loader.test_connection():
        raise ConnectionError("No se pudo conectar a Neon")
    if from_csv:
        return loader.load_consolidated_dataset(season_start=season_start, season_end=season_end)
    return loader.load_games(season_start=season_start, season_end=season_end)
