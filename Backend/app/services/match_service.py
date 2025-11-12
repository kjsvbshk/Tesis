"""
Match service for business logic
"""

from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from app.models.game import Game
from app.models.team import Team
from app.schemas.match import MatchCreate, MatchResponse, TeamBase

class MatchService:
    def __init__(self, db: Session):
        self.db = db
        self._table_columns = None
    
    def _find_column(self, available_columns: List[str], possible_names: List[str]) -> Optional[str]:
        """Encontrar una columna por nombre posible"""
        for name in possible_names:
            if name in available_columns:
                return name
        return None
    
    def _get_table_columns(self) -> Dict[str, str]:
        """Obtener las columnas reales de la tabla games con sus tipos"""
        if self._table_columns is None:
            try:
                # Intentar inspeccionar la tabla usando SQL directo
                result = self.db.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_schema = 'espn' AND table_name = 'games'
                    ORDER BY ordinal_position
                """))
                columns_data = result.fetchall()
                self._table_columns = {row[0]: row[1] for row in columns_data}
                
                if not self._table_columns:
                    # Si no hay columnas, la tabla puede no existir o tener otro nombre
                    # Intentar con inspector como fallback
                    try:
                        inspector = inspect(self.db.bind)
                        columns = inspector.get_columns('games', schema='espn')
                        self._table_columns = {col['name']: str(col.get('type', '')) for col in columns}
                    except:
                        pass
                
                if not self._table_columns:
                    # Último fallback: usar las columnas del modelo
                    self._table_columns = {col.name: str(col.type) for col in Game.__table__.columns}
                
                print(f"DEBUG: Found columns in espn.games: {list(self._table_columns.keys())}")
            except Exception as e:
                # Si falla, usar las columnas del modelo como fallback
                print(f"Warning: Could not inspect table structure: {e}")
                import traceback
                traceback.print_exc()
                self._table_columns = {col.name: str(col.type) for col in Game.__table__.columns}
        return self._table_columns
    
    def _game_to_dict(self, game: Game) -> Dict[str, Any]:
        """Convertir Game a dict para MatchResponse"""
        return {
            "id": game.id,
            "espn_id": game.espn_id,
            "home_team_id": game.home_team_id,
            "away_team_id": game.away_team_id,
            "game_date": game.game_date,
            "season": game.season,
            "season_type": game.season_type,
            "status": game.status,
            "home_score": game.home_score,
            "away_score": game.away_score,
            "winner_id": game.winner_id,
            "home_odds": game.home_odds,
            "away_odds": game.away_odds,
            "over_under": game.over_under,
            "created_at": game.created_at,
            "updated_at": game.updated_at,
            "home_team": {
                "id": game.home_team.id,
                "name": game.home_team.name,
                "abbreviation": game.home_team.abbreviation,
                "city": game.home_team.city,
                "conference": game.home_team.conference,
                "division": game.home_team.division,
            } if game.home_team else None,
            "away_team": {
                "id": game.away_team.id,
                "name": game.away_team.name,
                "abbreviation": game.away_team.abbreviation,
                "city": game.away_team.city,
                "conference": game.away_team.conference,
                "division": game.away_team.division,
            } if game.away_team else None,
            "winner": {
                "id": game.winner.id,
                "name": game.winner.name,
                "abbreviation": game.winner.abbreviation,
                "city": game.winner.city,
                "conference": game.winner.conference,
                "division": game.winner.division,
            } if game.winner else None,
        }
    
    async def get_matches(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[str] = None,
        team_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get matches with filters - completamente dinámico basado en la estructura real de la BD"""
        try:
            # Obtener columnas reales de la tabla
            columns_dict = self._get_table_columns()
            columns = list(columns_dict.keys())
            
            if not columns:
                raise Exception("No se encontraron columnas en la tabla espn.games")
            
            # Identificar columna de ID (puede ser 'id', 'game_id', o la primera columna)
            id_column = None
            for possible_id in ['id', 'game_id', 'games_id']:
                if possible_id in columns:
                    id_column = possible_id
                    break
            if not id_column:
                id_column = columns[0]  # Usar la primera columna como fallback
            
            # Mapeo de nombres de columnas esperados a posibles nombres reales
            column_mapping = {
                'id': id_column,
                'espn_id': self._find_column(columns, ['espn_id', 'espn_game_id', 'external_id']),
                'home_team_id': self._find_column(columns, ['home_team_id', 'home_team', 'team_home_id']),
                'away_team_id': self._find_column(columns, ['away_team_id', 'away_team', 'team_away_id']),
                'game_date': self._find_column(columns, ['game_date', 'date', 'game_time', 'scheduled_date']),
                'season': self._find_column(columns, ['season', 'season_year']),
                'season_type': self._find_column(columns, ['season_type', 'type', 'game_type']),
                'status': self._find_column(columns, ['status', 'game_status', 'state']),
                'home_score': self._find_column(columns, ['home_score', 'score_home', 'home_points']),
                'away_score': self._find_column(columns, ['away_score', 'score_away', 'away_points']),
                'winner_id': self._find_column(columns, ['winner_id', 'winner', 'winning_team_id']),
                'home_odds': self._find_column(columns, ['home_odds', 'odds_home']),
                'away_odds': self._find_column(columns, ['away_odds', 'odds_away']),
                'over_under': self._find_column(columns, ['over_under', 'total', 'overunder', 'total_points']),
                'created_at': self._find_column(columns, ['created_at', 'created', 'date_created']),
                'updated_at': self._find_column(columns, ['updated_at', 'updated', 'date_updated', 'modified_at']),
            }
            
            # Construir SELECT con columnas disponibles
            select_cols = []
            if column_mapping['id']:
                if column_mapping['id'] == 'id':
                    select_cols.append("g.id")
                else:
                    select_cols.append(f"g.{column_mapping['id']} AS id")
            
            for expected_name, actual_name in column_mapping.items():
                if expected_name != 'id' and actual_name:
                    select_cols.append(f"g.{actual_name}")
            
            if not select_cols:
                raise Exception("No se pudieron mapear columnas válidas")
            
            # Construir JOINs para teams si existen las columnas
            join_clause = ""
            team_select = ""
            home_team_col = column_mapping.get('home_team_id')
            away_team_col = column_mapping.get('away_team_id')
            
            if home_team_col and away_team_col:
                # Verificar si la tabla teams existe
                try:
                    teams_check = self.db.execute(text("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = 'espn' AND table_name = 'teams'
                    """))
                    if teams_check.scalar() > 0:
                        # Verificar el tipo de dato de las columnas para determinar cómo hacer el JOIN
                        # Intentar obtener una muestra para ver si son IDs (int) o nombres (string)
                        sample_query = f"""
                            SELECT {home_team_col}, {away_team_col} 
                            FROM espn.games 
                            WHERE {home_team_col} IS NOT NULL 
                            LIMIT 1
                        """
                        try:
                            sample_result = self.db.execute(text(sample_query))
                            sample_row = sample_result.fetchone()
                            home_is_string = False
                            away_is_string = False
                            
                            if sample_row:
                                # Verificar tipo de dato
                                home_val = sample_row[0]
                                away_val = sample_row[1] if len(sample_row) > 1 else None
                                home_is_string = isinstance(home_val, str)
                                away_is_string = isinstance(away_val, str) if away_val else False
                        except:
                            # Si no podemos determinar, asumir que son strings (nombres)
                            home_is_string = True
                            away_is_string = True
                        
                        # Construir JOIN según el tipo de dato
                        if home_is_string:
                            # Si es string, hacer JOIN por nombre
                            join_clause = f"""
                                LEFT JOIN espn.teams ht ON (g.{home_team_col} = ht.name OR g.{home_team_col} = ht.abbreviation)
                                LEFT JOIN espn.teams at ON (g.{away_team_col} = at.name OR g.{away_team_col} = at.abbreviation)
                            """
                        else:
                            # Si es int, hacer JOIN por ID
                            join_clause = f"""
                                LEFT JOIN espn.teams ht ON g.{home_team_col} = ht.id
                                LEFT JOIN espn.teams at ON g.{away_team_col} = at.id
                            """
                        
                        team_select = """
                            , ht.id as home_team_table_id, ht.name as home_team_name, 
                              COALESCE(ht.abbreviation, '') as home_team_abbr,
                              COALESCE(ht.city, '') as home_team_city,
                              COALESCE(ht.conference, '') as home_team_conf,
                              COALESCE(ht.division, '') as home_team_div,
                              at.id as away_team_table_id, at.name as away_team_name,
                              COALESCE(at.abbreviation, '') as away_team_abbr,
                              COALESCE(at.city, '') as away_team_city,
                              COALESCE(at.conference, '') as away_team_conf,
                              COALESCE(at.division, '') as away_team_div
                        """
                except:
                    pass  # Si no existe teams, continuar sin JOIN
            
            # Construir query SQL
            sql = f"""
                SELECT {', '.join(select_cols)}{team_select}
                FROM espn.games g
                {join_clause}
                WHERE 1=1
            """
            params = {}
            
            # Agregar filtros dinámicamente
            date_col = column_mapping.get('game_date')
            if date_from and date_col:
                sql += f" AND g.{date_col} >= :date_from"
                params['date_from'] = date_from
            if date_to and date_col:
                sql += f" AND g.{date_col} <= :date_to"
                params['date_to'] = date_to
            
            status_col = column_mapping.get('status')
            if status and status_col:
                sql += f" AND g.{status_col} = :status"
                params['status'] = status
            
            if team_id and home_team_col and away_team_col:
                sql += f" AND (g.{home_team_col} = :team_id OR g.{away_team_col} = :team_id)"
                params['team_id'] = team_id
            
            # Ordenar
            order_col = date_col if date_col else column_mapping['id']
            sql += f" ORDER BY g.{order_col} DESC LIMIT :limit OFFSET :offset"
            params['limit'] = limit
            params['offset'] = offset
            
            print(f"DEBUG SQL: {sql[:200]}...")
            print(f"DEBUG Params: {params}")
            
            # Ejecutar query
            result = self.db.execute(text(sql), params)
            rows = result.fetchall()
            
            # Convertir resultados a dict y resolver IDs de equipos
            matches = []
            for row in rows:
                match_dict = dict(row._mapping)
                
                # Obtener valores de home_team y away_team (pueden ser IDs o nombres)
                home_team_value = None
                away_team_value = None
                
                if column_mapping.get('home_team_id'):
                    home_team_value = match_dict.get(column_mapping['home_team_id'])
                if column_mapping.get('away_team_id'):
                    away_team_value = match_dict.get(column_mapping['away_team_id'])
                
                # Si tenemos datos del JOIN, usarlos directamente
                home_team_id_from_join = match_dict.get('home_team_table_id')
                away_team_id_from_join = match_dict.get('away_team_table_id')
                home_team_name_from_join = match_dict.get('home_team_name')
                away_team_name_from_join = match_dict.get('away_team_name')
                
                # Resolver IDs: si el valor es string, buscar en teams; si es int, usarlo directamente
                home_team_id = None
                away_team_id = None
                
                if home_team_id_from_join:
                    # Ya tenemos el ID del JOIN
                    home_team_id = int(home_team_id_from_join) if home_team_id_from_join else None
                elif home_team_value:
                    if isinstance(home_team_value, int):
                        home_team_id = home_team_value
                    elif isinstance(home_team_value, str):
                        # Es un nombre, buscar el ID en teams
                        try:
                            team_result = self.db.execute(text("""
                                SELECT id FROM espn.teams 
                                WHERE name = :name OR abbreviation = :name
                                LIMIT 1
                            """), {"name": home_team_value})
                            team_row = team_result.fetchone()
                            if team_row:
                                home_team_id = int(team_row[0])
                        except:
                            pass
                
                if away_team_id_from_join:
                    # Ya tenemos el ID del JOIN
                    away_team_id = int(away_team_id_from_join) if away_team_id_from_join else None
                elif away_team_value:
                    if isinstance(away_team_value, int):
                        away_team_id = away_team_value
                    elif isinstance(away_team_value, str):
                        # Es un nombre, buscar el ID en teams
                        try:
                            team_result = self.db.execute(text("""
                                SELECT id FROM espn.teams 
                                WHERE name = :name OR abbreviation = :name
                                LIMIT 1
                            """), {"name": away_team_value})
                            team_row = team_result.fetchone()
                            if team_row:
                                away_team_id = int(team_row[0])
                        except:
                            pass
                
                # Obtener nombres de equipos si no los tenemos del JOIN
                home_team_name = home_team_name_from_join
                away_team_name = away_team_name_from_join
                
                if not home_team_name and home_team_value and isinstance(home_team_value, str):
                    home_team_name = home_team_value
                if not away_team_name and away_team_value and isinstance(away_team_value, str):
                    away_team_name = away_team_value
                
                # Si tenemos IDs pero no nombres, buscar los nombres y otros datos
                home_team_abbr = match_dict.get('home_team_abbr') or ''
                home_team_city = match_dict.get('home_team_city') or ''
                home_team_conf = match_dict.get('home_team_conf') or ''
                home_team_div = match_dict.get('home_team_div') or ''
                
                if home_team_id and not home_team_name:
                    try:
                        team_result = self.db.execute(text("SELECT name, abbreviation, city, conference, division FROM espn.teams WHERE id = :id"), {"id": home_team_id})
                        team_row = team_result.fetchone()
                        if team_row:
                            home_team_name = team_row[0]
                            home_team_abbr = team_row[1] or ''
                            home_team_city = team_row[2] or ''
                            home_team_conf = team_row[3] or ''
                            home_team_div = team_row[4] or ''
                    except:
                        pass
                
                away_team_abbr = match_dict.get('away_team_abbr') or ''
                away_team_city = match_dict.get('away_team_city') or ''
                away_team_conf = match_dict.get('away_team_conf') or ''
                away_team_div = match_dict.get('away_team_div') or ''
                
                if away_team_id and not away_team_name:
                    try:
                        team_result = self.db.execute(text("SELECT name, abbreviation, city, conference, division FROM espn.teams WHERE id = :id"), {"id": away_team_id})
                        team_row = team_result.fetchone()
                        if team_row:
                            away_team_name = team_row[0]
                            away_team_abbr = team_row[1] or ''
                            away_team_city = team_row[2] or ''
                            away_team_conf = team_row[3] or ''
                            away_team_div = team_row[4] or ''
                    except:
                        pass
                
                # Si tenemos nombres pero no IDs, intentar buscar IDs una vez más
                if not home_team_id and home_team_name:
                    try:
                        team_result = self.db.execute(text("""
                            SELECT id, abbreviation, city, conference, division FROM espn.teams 
                            WHERE name = :name OR abbreviation = :name
                            LIMIT 1
                        """), {"name": home_team_name})
                        team_row = team_result.fetchone()
                        if team_row:
                            home_team_id = int(team_row[0])
                            if not home_team_abbr:
                                home_team_abbr = team_row[1] or ''
                            if not home_team_city:
                                home_team_city = team_row[2] or ''
                            if not home_team_conf:
                                home_team_conf = team_row[3] or ''
                            if not home_team_div:
                                home_team_div = team_row[4] or ''
                    except:
                        pass
                
                if not away_team_id and away_team_name:
                    try:
                        team_result = self.db.execute(text("""
                            SELECT id, abbreviation, city, conference, division FROM espn.teams 
                            WHERE name = :name OR abbreviation = :name
                            LIMIT 1
                        """), {"name": away_team_name})
                        team_row = team_result.fetchone()
                        if team_row:
                            away_team_id = int(team_row[0])
                            if not away_team_abbr:
                                away_team_abbr = team_row[1] or ''
                            if not away_team_city:
                                away_team_city = team_row[2] or ''
                            if not away_team_conf:
                                away_team_conf = team_row[3] or ''
                            if not away_team_div:
                                away_team_div = team_row[4] or ''
                    except:
                        pass
                
                # Construir objeto MatchResponse con mapeo dinámico
                match = {
                    "id": match_dict.get('id') or match_dict.get(column_mapping['id']),
                    "espn_id": match_dict.get(column_mapping['espn_id']) if column_mapping['espn_id'] else None,
                    "home_team_id": int(home_team_id) if home_team_id else None,
                    "away_team_id": int(away_team_id) if away_team_id else None,
                    "game_date": match_dict.get(column_mapping['game_date']) if column_mapping['game_date'] else None,
                    "season": match_dict.get(column_mapping['season']) if column_mapping['season'] else None,
                    "season_type": match_dict.get(column_mapping['season_type']) if column_mapping['season_type'] else None,
                    "status": match_dict.get(column_mapping['status']) if column_mapping['status'] else None,
                    "home_score": match_dict.get(column_mapping['home_score']) if column_mapping['home_score'] else None,
                    "away_score": match_dict.get(column_mapping['away_score']) if column_mapping['away_score'] else None,
                    "winner_id": match_dict.get(column_mapping['winner_id']) if column_mapping['winner_id'] else None,
                    "home_odds": match_dict.get(column_mapping['home_odds']) if column_mapping['home_odds'] else None,
                    "away_odds": match_dict.get(column_mapping['away_odds']) if column_mapping['away_odds'] else None,
                    "over_under": match_dict.get(column_mapping['over_under']) if column_mapping['over_under'] else None,
                    "created_at": match_dict.get(column_mapping['created_at']) if column_mapping['created_at'] else None,
                    "updated_at": match_dict.get(column_mapping['updated_at']) if column_mapping['updated_at'] else None,
                    "home_team": {
                        "id": int(home_team_id) if home_team_id else 0,
                        "name": home_team_name or (home_team_value if isinstance(home_team_value, str) else 'Unknown'),
                        "abbreviation": home_team_abbr,
                        "city": home_team_city,
                        "conference": home_team_conf,
                        "division": home_team_div,
                    } if (home_team_id or home_team_name or (home_team_value and isinstance(home_team_value, str))) else None,
                    "away_team": {
                        "id": int(away_team_id) if away_team_id else 0,
                        "name": away_team_name or (away_team_value if isinstance(away_team_value, str) else 'Unknown'),
                        "abbreviation": away_team_abbr,
                        "city": away_team_city,
                        "conference": away_team_conf,
                        "division": away_team_div,
                    } if (away_team_id or away_team_name or (away_team_value and isinstance(away_team_value, str))) else None,
                    "winner": None,
                }
                matches.append(match)
            
            return matches
        except Exception as e:
            # Si falla, intentar con ORM como fallback
            try:
                query = self.db.query(Game)
                
                if date_from:
                    query = query.filter(Game.game_date >= date_from)
                if date_to:
                    query = query.filter(Game.game_date <= date_to)
                if status:
                    query = query.filter(Game.status == status)
                if team_id:
                    query = query.filter(
                        (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
                    )
                
                games = query.offset(offset).limit(limit).all()
                
                result = []
                for game in games:
                    game.home_team = self.db.query(Team).filter(Team.id == game.home_team_id).first()
                    game.away_team = self.db.query(Team).filter(Team.id == game.away_team_id).first()
                    if game.winner_id:
                        game.winner = self.db.query(Team).filter(Team.id == game.winner_id).first()
                    
                    result.append(self._game_to_dict(game))
                
                return result
            except Exception as orm_error:
                import traceback
                traceback.print_exc()
                raise Exception(f"Error fetching matches (SQL and ORM failed): {str(e)} | {str(orm_error)}")
    
    async def get_match_by_id(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Get match by ID"""
        try:
            game = self.db.query(Game).filter(Game.id == match_id).first()
            if not game:
                return None
            
            # Cargar relaciones
            game.home_team = self.db.query(Team).filter(Team.id == game.home_team_id).first()
            game.away_team = self.db.query(Team).filter(Team.id == game.away_team_id).first()
            if game.winner_id:
                game.winner = self.db.query(Team).filter(Team.id == game.winner_id).first()
            
            return self._game_to_dict(game)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception(f"Error fetching match: {str(e)}")
    
    async def create_match(self, match: MatchCreate) -> Game:
        """Create a new match"""
        db_match = Game(**match.dict())
        self.db.add(db_match)
        self.db.commit()
        self.db.refresh(db_match)
        return db_match
    
    async def update_match(self, match_id: int, match_update: dict) -> Optional[Game]:
        """Update match information"""
        db_match = await self.get_match_by_id(match_id)
        if not db_match:
            return None
        
        for field, value in match_update.items():
            if hasattr(db_match, field):
                setattr(db_match, field, value)
        
        self.db.commit()
        self.db.refresh(db_match)
        return db_match
    
    async def get_teams(self) -> List[Team]:
        """Get all teams"""
        return self.db.query(Team).all()
    
    async def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """Get team by ID"""
        return self.db.query(Team).filter(Team.id == team_id).first()
