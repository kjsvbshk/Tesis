"""
Data loader for ML training
Carga datos desde PostgreSQL (Neon) para entrenar modelos
"""

import pandas as pd
from sqlalchemy import create_engine, text
from typing import Optional, Dict, Any
from datetime import datetime, date
import os

from src.config import db_config


class DataLoader:
    """Carga datos desde Neon PostgreSQL para entrenamiento"""
    
    def __init__(self, schema: str = "espn"):
        """
        Inicializa el cargador de datos
        
        Args:
            schema: Esquema a usar - "espn" (datos NBA), "app" (sistema), o "ml" (ML)
        """
        self.schema = db_config.get_schema(schema)
        self.database_url = db_config.get_database_url()
        
        # Crear engine
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
    
    def load_games(
        self,
        season_start: Optional[str] = None,
        season_end: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Carga partidos desde la base de datos
        
        Args:
            season_start: Fecha de inicio de temporada (YYYY-MM-DD)
            season_end: Fecha de fin de temporada (YYYY-MM-DD)
            limit: Límite de registros a cargar
        
        Returns:
            DataFrame con partidos
        """
        # Intentar diferentes nombres de columna de fecha
        date_columns = ["game_date", "date", "match_date", "played_at"]
        
        query = f"""
        SELECT *
        FROM {self.schema}.games
        WHERE 1=1
        """
        
        params = {}
        
        # Intentar agregar filtros de fecha si se especifican
        # Primero necesitamos saber qué columna de fecha existe
        if season_start or season_end:
            # Por ahora, intentar con game_date (se puede ajustar después)
            if season_start:
                query += " AND (game_date >= :season_start OR date >= :season_start)"
                params['season_start'] = season_start
            if season_end:
                query += " AND (game_date <= :season_end OR date <= :season_end)"
                params['season_end'] = season_end
        
        # Ordenar por fecha (intentar diferentes columnas)
        query += " ORDER BY COALESCE(game_date, date, match_date) DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        with self.engine.connect() as conn:
            # Establecer search_path si es necesario
            if self.schema:
                conn.execute(text(f"SET search_path TO {self.schema}, public"))
                conn.commit()
            
            df = pd.read_sql(text(query), conn, params=params)
        
        return df
    
    def load_team_stats(
        self,
        season: Optional[str] = None,
        game_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Carga estadísticas de equipos
        
        Args:
            season: Temporada (e.g., "2023-24")
            game_date: Fecha específica del partido
        
        Returns:
            DataFrame con estadísticas de equipos
        """
        query = f"""
        SELECT *
        FROM {self.schema}.team_stats
        WHERE 1=1
        """
        
        params = {}
        
        if season:
            query += " AND season = :season"
            params['season'] = season
        
        if game_date:
            query += " AND (game_date = :game_date OR date = :game_date)"
            params['game_date'] = game_date
        
        query += " ORDER BY COALESCE(game_date, date) DESC"
        
        with self.engine.connect() as conn:
            if self.schema:
                conn.execute(text(f"SET search_path TO {self.schema}, public"))
                conn.commit()
            
            df = pd.read_sql(text(query), conn, params=params)
        
        return df
    
    def load_standings(
        self,
        season: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Carga clasificaciones
        
        Args:
            season: Temporada (e.g., "2023-24")
        
        Returns:
            DataFrame con clasificaciones
        """
        query = f"""
        SELECT *
        FROM {self.schema}.standings
        WHERE 1=1
        """
        
        params = {}
        
        if season:
            query += " AND season = :season"
            params['season'] = season
        
        query += " ORDER BY season DESC, wins DESC"
        
        with self.engine.connect() as conn:
            if self.schema:
                conn.execute(text(f"SET search_path TO {self.schema}, public"))
                conn.commit()
            
            df = pd.read_sql(text(query), conn, params=params)
        
        return df
    
    def load_injuries(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Carga reportes de lesiones
        
        Args:
            date_from: Fecha desde
            date_to: Fecha hasta
        
        Returns:
            DataFrame con lesiones
        """
        query = f"""
        SELECT *
        FROM {self.schema}.injuries
        WHERE 1=1
        """
        
        params = {}
        
        if date_from:
            query += " AND (injury_date >= :date_from OR date >= :date_from)"
            params['date_from'] = date_from
        
        if date_to:
            query += " AND (injury_date <= :date_to OR date <= :date_to)"
            params['date_to'] = date_to
        
        query += " ORDER BY COALESCE(injury_date, date) DESC"
        
        with self.engine.connect() as conn:
            if self.schema:
                conn.execute(text(f"SET search_path TO {self.schema}, public"))
                conn.commit()
            
            df = pd.read_sql(text(query), conn, params=params)
        
        return df
    
    def load_odds(
        self,
        game_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Carga cuotas de apuestas
        
        Args:
            game_date: Fecha del partido
        
        Returns:
            DataFrame con cuotas
        """
        query = f"""
        SELECT *
        FROM {self.schema}.odds
        WHERE 1=1
        """
        
        params = {}
        
        if game_date:
            query += " AND (game_date = :game_date OR date = :game_date)"
            params['game_date'] = game_date
        
        query += " ORDER BY COALESCE(game_date, date) DESC"
        
        with self.engine.connect() as conn:
            if self.schema:
                conn.execute(text(f"SET search_path TO {self.schema}, public"))
                conn.commit()
            
            df = pd.read_sql(text(query), conn, params=params)
        
        return df
    
    def load_consolidated_dataset(
        self,
        season_start: Optional[str] = None,
        season_end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Carga dataset consolidado (si existe en CSV procesado)
        Si no existe, intenta construir desde las tablas
        
        Args:
            season_start: Fecha de inicio
            season_end: Fecha de fin
        
        Returns:
            DataFrame consolidado
        """
        # Primero intentar cargar desde CSV procesado
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "..", "Scrapping", "nba", "data", "processed", "nba_full_dataset.csv"
        )
        
        if os.path.exists(csv_path):
            print(f"📁 Cargando dataset consolidado desde: {csv_path}")
            df = pd.read_csv(csv_path)
            
            # Filtrar por fechas si se especifican
            if season_start or season_end:
                if 'date' in df.columns or 'game_date' in df.columns:
                    date_col = 'date' if 'date' in df.columns else 'game_date'
                    df[date_col] = pd.to_datetime(df[date_col])
                    
                    if season_start:
                        df = df[df[date_col] >= pd.to_datetime(season_start)]
                    if season_end:
                        df = df[df[date_col] <= pd.to_datetime(season_end)]
            
            return df
        else:
            print(f"⚠️  CSV consolidado no encontrado en {csv_path}")
            print("   Construyendo dataset desde tablas de base de datos...")
            
            # Construir dataset desde tablas
            games = self.load_games(season_start=season_start, season_end=season_end)
            
            if games.empty:
                print("❌ No se encontraron partidos en la base de datos")
                return pd.DataFrame()
            
            # Aquí se podría hacer un join con otras tablas
            # Por ahora, retornar solo games
            return games
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a la base de datos
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            with self.engine.connect() as conn:
                if self.schema:
                    conn.execute(text(f"SET search_path TO {self.schema}, public"))
                    conn.commit()
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            return True
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False


def load_nba_data(
    season_start: Optional[str] = None,
    season_end: Optional[str] = None,
    from_csv: bool = True
) -> pd.DataFrame:
    """
    Función de conveniencia para cargar datos NBA desde Neon
    
    Args:
        season_start: Fecha de inicio (YYYY-MM-DD)
        season_end: Fecha de fin (YYYY-MM-DD)
        from_csv: Si True, intenta cargar desde CSV primero
    
    Returns:
        DataFrame con datos NBA
    """
    loader = DataLoader(schema="espn")
    
    if not loader.test_connection():
        raise ConnectionError("No se pudo conectar a Neon")
    
    if from_csv:
        return loader.load_consolidated_dataset(season_start=season_start, season_end=season_end)
    else:
        return loader.load_games(season_start=season_start, season_end=season_end)
