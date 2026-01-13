"""
Snapshot Service for RF-07
Captura snapshots de odds desde el esquema espn
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.models import OddsSnapshot, OddsLine
from app.core.database import espn_engine
from app.services.db_schema_service import DBSchemaService


class SnapshotService:
    """Service for creating odds snapshots from espn schema"""
    
    def __init__(self, db: Session):
        self.db = db
        self.schema_service = DBSchemaService(db)
    
    async def create_snapshot_for_request(
        self,
        request_id: int,
        game_id: Optional[int] = None
    ) -> OddsSnapshot:
        """
        Crea un snapshot de odds para un request
        Si se proporciona game_id, busca odds específicas de ese juego
        Si no, busca las odds más recientes disponibles
        """
        # Crear snapshot
        snapshot = OddsSnapshot(
            request_id=request_id,
            taken_at=datetime.utcnow()
        )
        self.db.add(snapshot)
        self.db.flush()  # Para obtener el ID
        
        # Obtener odds desde esquema espn
        odds_data = await self._fetch_odds_from_espn(game_id)
        
        # Crear odds_lines desde los datos de espn
        for odds_line_data in odds_data:
            odds_line = OddsLine(
                snapshot_id=snapshot.id,
                provider_id=None,  # Viene de espn, no de provider externo
                source="espn",
                line_code=odds_line_data["line_code"],
                price=odds_line_data["price"],
                line_metadata=json.dumps(odds_line_data.get("metadata", {}))
            )
            self.db.add(odds_line)
        
        self.db.commit()
        self.db.refresh(snapshot)
        
        return snapshot
    
    async def _fetch_odds_from_espn(self, game_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene odds desde el esquema espn
        Retorna lista de odds_lines para guardar en snapshot
        """
        odds_lines = []
        odds_dict = {}
        
        # Inspeccionar estructura real de las tablas
        games_columns = self.schema_service.get_table_columns('games', 'espn')
        odds_columns = self.schema_service.get_table_columns('odds', 'espn')
        
        # Buscar columnas relevantes en games (basado en estructura real de Neon)
        # En Neon: game_id (bigint), fecha (date), home_team (varchar), away_team (varchar)
        games_id_col = self.schema_service.find_column('games', ['game_id', 'id'], 'espn')
        games_date_col = self.schema_service.find_column('games', ['fecha', 'game_date', 'date'], 'espn')
        
        # Buscar columnas relevantes en odds (basado en estructura real de Neon)
        # En Neon: game_id (varchar), commence_time (varchar), home_team (varchar), away_team (varchar)
        odds_game_id_col = self.schema_service.find_column('odds', ['game_id'], 'espn')
        odds_commence_time_col = self.schema_service.find_column('odds', ['commence_time'], 'espn')
        
        with espn_engine.connect() as conn:
            conn.execute(text("SET search_path TO espn, public"))
            conn.commit()
            
            if game_id:
                # En Neon, games.game_id es bigint, pero odds.game_id es varchar
                # Necesitamos convertir el game_id a string para buscar en odds
                game_id_str = str(game_id)
                
                # Intentar buscar odds por game_id directamente (odds.game_id es varchar)
                if odds_game_id_col and games_id_col:
                    # Buscar en odds usando game_id como string
                    odds_result = conn.execute(
                        text(f"SELECT * FROM odds WHERE {odds_game_id_col} = :game_id ORDER BY {odds_commence_time_col or 'commence_time'} DESC LIMIT 1"),
                        {"game_id": game_id_str}
                    ).fetchone()
                    
                    if odds_result:
                        odds_dict = dict(odds_result._mapping)
                    else:
                        # Si no hay coincidencia directa, buscar por fecha del juego
                        if games_date_col:
                            game_result = conn.execute(
                                text(f"SELECT {games_date_col} FROM games WHERE {games_id_col} = :game_id"),
                                {"game_id": game_id}
                            ).fetchone()
                            
                            if game_result and game_result[0] and odds_commence_time_col:
                                # Buscar odds por fecha aproximada
                                # En Neon, commence_time es varchar, necesitamos parsearlo
                                try:
                                    game_date = game_result[0]
                                    # Intentar buscar por fecha (commence_time es varchar, puede necesitar casting)
                                    # Cast la columna a date y comparar con el parámetro (que ya es date)
                                    odds_result = conn.execute(
                                        text(f"SELECT * FROM odds WHERE CAST({odds_commence_time_col} AS date) = CAST(:game_date AS date) ORDER BY {odds_commence_time_col} DESC LIMIT 1"),
                                        {"game_date": game_date}
                                    ).fetchone()
                                    if odds_result:
                                        odds_dict = dict(odds_result._mapping)
                                except Exception as e:
                                    print(f"⚠️  Error searching odds by date: {e}")
                                    # Si falla el casting, intentar búsqueda por coincidencia de texto
                                    try:
                                        date_str = str(game_date)
                                        odds_result = conn.execute(
                                            text(f"SELECT * FROM odds WHERE {odds_commence_time_col} LIKE :date_pattern ORDER BY {odds_commence_time_col} DESC LIMIT 1"),
                                            {"date_pattern": f"{date_str}%"}
                                        ).fetchone()
                                        if odds_result:
                                            odds_dict = dict(odds_result._mapping)
                                    except Exception as e2:
                                        print(f"⚠️  Error in text search: {e2}")
                                    odds_result = None
                        else:
                            odds_result = None
                else:
                    # Si no podemos mapear las columnas, intentar obtener odds más recientes
                    print(f"⚠️  Cannot map game_id to odds, using most recent odds")
                    odds_result = None
            else:
                # Obtener odds más recientes
                if odds_commence_time_col:
                    odds_result = conn.execute(
                        text(f"SELECT * FROM odds ORDER BY {odds_commence_time_col} DESC LIMIT 1")
                    ).fetchone()
                else:
                    odds_result = conn.execute(
                        text("SELECT * FROM odds ORDER BY id DESC LIMIT 1")
                    ).fetchone()
            
            if not odds_dict and odds_result:
                odds_dict = dict(odds_result._mapping)
            
            if odds_dict:
                bookmakers = odds_dict.get("bookmakers", []) if isinstance(odds_dict.get("bookmakers"), list) else []
                
                # Procesar bookmakers y crear odds_lines
                for bookmaker in bookmakers:
                    bookmaker_key = bookmaker.get("key", "unknown")
                    bookmaker_title = bookmaker.get("title", "Unknown")
                    
                    for market in bookmaker.get("markets", []):
                        market_key = market.get("key", "unknown")
                        
                        for outcome in market.get("outcomes", []):
                            outcome_name = outcome.get("name", "")
                            outcome_price = outcome.get("price")
                            outcome_point = outcome.get("point")
                            
                            if outcome_price:
                                # Crear line_code basado en market y outcome
                                if market_key == "h2h":
                                    # Head to head: determinar si es home o away
                                    home_team = odds_dict.get("home_team", "")
                                    away_team = odds_dict.get("away_team", "")
                                    
                                    if outcome_name == home_team:
                                        line_code = "home_win"
                                    elif outcome_name == away_team:
                                        line_code = "away_win"
                                    else:
                                        line_code = f"h2h_{outcome_name.lower().replace(' ', '_')}"
                                elif market_key == "spreads":
                                    # Spread bets
                                    if outcome_point:
                                        line_code = f"spread_{outcome_name.lower().replace(' ', '_')}_{outcome_point}"
                                    else:
                                        line_code = f"spread_{outcome_name.lower().replace(' ', '_')}"
                                elif market_key == "totals":
                                    # Over/Under
                                    if outcome_point:
                                        over_under = "over" if "over" in outcome_name.lower() else "under"
                                        line_code = f"total_{over_under}_{outcome_point}"
                                    else:
                                        line_code = f"total_{outcome_name.lower().replace(' ', '_')}"
                                else:
                                    line_code = f"{market_key}_{outcome_name.lower().replace(' ', '_')}"
                                
                                odds_lines.append({
                                    "line_code": line_code,
                                    "price": float(outcome_price),
                                    "metadata": {
                                        "bookmaker": bookmaker_key,
                                        "bookmaker_title": bookmaker_title,
                                        "market": market_key,
                                        "outcome_name": outcome_name,
                                        "point": outcome_point,
                                        "game_id": odds_dict.get("game_id"),
                                        "commence_time": odds_dict.get("commence_time")
                                    }
                                })
        
        return odds_lines
    
    async def get_snapshot_by_request_id(self, request_id: int) -> Optional[OddsSnapshot]:
        """Obtiene el snapshot más reciente para un request"""
        return self.db.query(OddsSnapshot).filter(
            OddsSnapshot.request_id == request_id
        ).order_by(OddsSnapshot.taken_at.desc()).first()
    
    async def get_snapshot_with_lines(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un snapshot con sus odds_lines"""
        snapshot = self.db.query(OddsSnapshot).filter(
            OddsSnapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            return None
        
        odds_lines = self.db.query(OddsLine).filter(
            OddsLine.snapshot_id == snapshot_id
        ).all()
        
        return {
            "snapshot": snapshot,
            "odds_lines": odds_lines,
            "total_lines": len(odds_lines)
        }

