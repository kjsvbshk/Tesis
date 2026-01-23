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
        # En Neon: external_event_id (varchar - ID de The Odds API), commence_time (varchar), home_team (varchar), away_team (varchar)
        odds_external_event_id_col = self.schema_service.find_column('odds', ['external_event_id', 'game_id'], 'espn')
        odds_commence_time_col = self.schema_service.find_column('odds', ['commence_time'], 'espn')
        odds_home_team_col = self.schema_service.find_column('odds', ['home_team'], 'espn')
        odds_away_team_col = self.schema_service.find_column('odds', ['away_team'], 'espn')
        
        with espn_engine.connect() as conn:
            conn.execute(text("SET search_path TO espn, public"))
            conn.commit()
            
            if game_id:
                # PASO 1: Buscar mapeo en odds_event_game_map
                mapping_result = conn.execute(
                    text("""
                        SELECT external_event_id, resolution_confidence
                        FROM espn.odds_event_game_map
                        WHERE game_id = :game_id
                        ORDER BY last_verified_at DESC NULLS LAST, created_at DESC
                        LIMIT 1
                    """),
                    {"game_id": game_id}
                ).fetchone()
                
                external_event_id = None
                if mapping_result:
                    external_event_id = mapping_result[0]
                    resolution_confidence = mapping_result[1] if len(mapping_result) > 1 else None
                    print(f"✅ Mapeo encontrado: game_id={game_id} → external_event_id={external_event_id} (confianza: {resolution_confidence})")
                
                # PASO 2: Si hay mapeo, buscar odds usando external_event_id
                if external_event_id and odds_external_event_id_col:
                    odds_result = conn.execute(
                        text(f"SELECT * FROM odds WHERE {odds_external_event_id_col} = :external_event_id ORDER BY {odds_commence_time_col or 'commence_time'} DESC LIMIT 1"),
                        {"external_event_id": external_event_id}
                    ).fetchone()
                    
                    if odds_result:
                        odds_dict = dict(odds_result._mapping)
                
                # PASO 3: Si no hay mapeo o no se encontraron odds, intentar resolver por fecha/equipos
                if not odds_dict and games_date_col:
                    # Obtener información del juego
                    game_result = conn.execute(
                        text(f"SELECT {games_date_col}, home_team, away_team FROM games WHERE {games_id_col} = :game_id"),
                        {"game_id": game_id}
                    ).fetchone()
                    
                    if game_result:
                        game_date = game_result[0]
                        game_home_team = game_result[1] if len(game_result) > 1 else None
                        game_away_team = game_result[2] if len(game_result) > 2 else None
                        
                        # Buscar odds por fecha y equipos
                        if odds_commence_time_col:
                            try:
                                # Construir query de búsqueda por fecha
                                date_query = f"CAST({odds_commence_time_col} AS date) = CAST(:game_date AS date)"
                                
                                # Si tenemos equipos, agregar filtro por equipos
                                if game_home_team and game_away_team and odds_home_team_col and odds_away_team_col:
                                    team_query = f"(({odds_home_team_col} ILIKE :home_team AND {odds_away_team_col} ILIKE :away_team) OR ({odds_home_team_col} ILIKE :away_team AND {odds_away_team_col} ILIKE :home_team))"
                                    full_query = f"{date_query} AND {team_query}"
                                    params = {
                                        "game_date": game_date,
                                        "home_team": f"%{game_home_team}%",
                                        "away_team": f"%{game_away_team}%"
                                    }
                                else:
                                    full_query = date_query
                                    params = {"game_date": game_date}
                                
                                odds_result = conn.execute(
                                    text(f"SELECT * FROM odds WHERE {full_query} ORDER BY {odds_commence_time_col} DESC LIMIT 1"),
                                    params
                                ).fetchone()
                                
                                if odds_result:
                                    odds_dict = dict(odds_result._mapping)
                                    
                                    # Crear mapeo para futuras búsquedas (FASE 4.1: NO actualizar automáticamente)
                                    external_event_id_from_odds = odds_dict.get(odds_external_event_id_col or 'external_event_id')
                                    if external_event_id_from_odds:
                                        try:
                                            # Verificar si ya existe mapping
                                            existing_mapping = conn.execute(
                                                text("""
                                                    SELECT id, game_id, resolution_confidence, needs_review
                                                    FROM espn.odds_event_game_map
                                                    WHERE external_event_id = :external_event_id
                                                """),
                                                {"external_event_id": external_event_id_from_odds}
                                            ).fetchone()
                                            
                                            if existing_mapping:
                                                # Mapping existe: NO actualizar automáticamente (política FASE 4.1)
                                                existing_game_id = existing_mapping[1]
                                                if existing_game_id != game_id:
                                                    print(f"⚠️  Mapping existente con game_id diferente: {existing_game_id} vs {game_id}. NO se actualiza automáticamente.")
                                                else:
                                                    print(f"ℹ️  Mapping ya existe: external_event_id={external_event_id_from_odds} → game_id={game_id}")
                                            else:
                                                # Mapping no existe: crear nuevo
                                                # Calcular confianza basada en método de resolución
                                                has_teams = game_home_team and game_away_team
                                                resolution_method = "auto_date_team" if has_teams else "auto_date_only"
                                                # Confianza: alta si tiene equipos, media si solo fecha
                                                resolution_confidence = "high" if has_teams else "medium"
                                                
                                                conn.execute(
                                                    text("""
                                                        INSERT INTO espn.odds_event_game_map 
                                                        (external_event_id, game_id, resolved_by, resolution_method, resolution_confidence, resolution_metadata)
                                                        VALUES (:external_event_id, :game_id, :resolved_by, :resolution_method, :confidence, :metadata)
                                                    """),
                                                    {
                                                        "external_event_id": external_event_id_from_odds,
                                                        "game_id": game_id,
                                                        "resolved_by": "date_teams" if has_teams else "date",
                                                        "resolution_method": resolution_method,
                                                        "confidence": resolution_confidence,
                                                        "metadata": f'{{"game_date": "{game_date}", "home_team": "{game_home_team}", "away_team": "{game_away_team}"}}'
                                                    }
                                                )
                                                conn.commit()
                                                print(f"✅ Mapeo creado: external_event_id={external_event_id_from_odds} → game_id={game_id} (método: {resolution_method}, confianza: {resolution_confidence})")
                                        except Exception as e:
                                            print(f"⚠️  Error creando mapeo: {e}")
                                            conn.rollback()
                            except Exception as e:
                                print(f"⚠️  Error searching odds by date/teams: {e}")
                                # Fallback: buscar solo por fecha con LIKE
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
                                        "external_event_id": odds_dict.get("external_event_id"),
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

