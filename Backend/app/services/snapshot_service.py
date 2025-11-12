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


class SnapshotService:
    """Service for creating odds snapshots from espn schema"""
    
    def __init__(self, db: Session):
        self.db = db
    
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
        
        with espn_engine.connect() as conn:
            conn.execute(text("SET search_path TO espn, public"))
            conn.commit()
            
            if game_id:
                # Buscar odds por game_id (usando espn_id del game)
                game_result = conn.execute(
                    text("SELECT espn_id FROM games WHERE id = :game_id"),
                    {"game_id": game_id}
                ).fetchone()
                
                if game_result and game_result[0]:
                    espn_game_id = game_result[0]
                    odds_result = conn.execute(
                        text("SELECT * FROM odds WHERE game_id = :game_id ORDER BY commence_time DESC LIMIT 1"),
                        {"game_id": espn_game_id}
                    ).fetchone()
                else:
                    # Si no hay espn_id, buscar por fecha del juego
                    game_result = conn.execute(
                        text("SELECT game_date FROM games WHERE id = :game_id"),
                        {"game_id": game_id}
                    ).fetchone()
                    if game_result:
                        # Buscar odds por fecha aproximada
                        odds_result = conn.execute(
                            text("SELECT * FROM odds WHERE commence_time::date = :game_date::date ORDER BY commence_time DESC LIMIT 1"),
                            {"game_date": game_result[0]}
                        ).fetchone()
                    else:
                        odds_result = None
            else:
                # Obtener odds más recientes
                odds_result = conn.execute(
                    text("SELECT * FROM odds ORDER BY commence_time DESC LIMIT 1")
                ).fetchone()
            
            if odds_result:
                odds_dict = dict(odds_result._mapping)
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

