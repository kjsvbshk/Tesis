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
from app.services.db_schema_service import DBSchemaService

class MatchService:
    def __init__(self, db: Session):
        self.db = db
        self.schema_service = DBSchemaService(db)
        self._table_columns = None
    
    def _find_column(self, possible_names: List[str]) -> Optional[str]:
        """Encontrar una columna por nombre posible"""
        # Usar el servicio de esquema para buscar la columna
        return self.schema_service.find_column('games', possible_names, 'espn')
    
    def _get_table_columns(self) -> Dict[str, str]:
        """Obtener las columnas reales de la tabla games con sus tipos"""
        if self._table_columns is None:
            # Usar el servicio de esquema para obtener columnas reales
            self._table_columns = self.schema_service.get_table_columns('games', 'espn')
            
            # Si no se encontraron columnas, usar fallback del modelo
            if not self._table_columns:
                print(f"⚠️  No columns found via schema service, using model fallback")
                self._table_columns = {col.name: str(col.type) for col in Game.__table__.columns}
        return self._table_columns
    
    def _game_to_dict(self, game: Game) -> Dict[str, Any]:
        """Convertir Game a dict para MatchResponse"""
        return {
            "id": game.game_id,
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
                "id": game.home_team.team_id,
                "name": game.home_team.name,
                "abbreviation": game.home_team.abbreviation,
                "city": game.home_team.city,
                "conference": game.home_team.conference,
                "division": game.home_team.division,
            } if game.home_team else None,
            "away_team": {
                "id": game.away_team.team_id,
                "name": game.away_team.name,
                "abbreviation": game.away_team.abbreviation,
                "city": game.away_team.city,
                "conference": game.away_team.conference,
                "division": game.away_team.division,
            } if game.away_team else None,
            "winner": {
                "id": game.winner.team_id,
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
        """Get matches with filters - usa solo las columnas que realmente existen en la BD"""
        try:
            # Obtener columnas reales de la tabla
            columns_dict = self._get_table_columns()
            columns = list(columns_dict.keys())
            
            if not columns:
                raise Exception("No se encontraron columnas en la tabla espn.games")
            
            print(f"🔍 Columnas encontradas en espn.games: {columns}")
            
            # Identificar columna de ID - buscar game_id primero
            id_column = self._find_column(['game_id', 'id'])
            if not id_column:
                id_column = columns[0]  # Usar la primera columna como fallback
            print(f"✅ ID column: {id_column}")
            
            # Buscar solo las columnas que realmente existen en la tabla games
            # Según la estructura real: game_id, fecha, home_team, away_team, home_score, away_score
            home_team_col = self._find_column(['home_team'])
            away_team_col = self._find_column(['away_team'])
            date_col = self._find_column(['fecha'])
            home_score_col = self._find_column(['home_score'])
            away_score_col = self._find_column(['away_score'])
            
            print(f"📊 Columnas mapeadas (solo las que existen):")
            print(f"   - home_team: {home_team_col}")
            print(f"   - away_team: {away_team_col}")
            print(f"   - fecha: {date_col}")
            print(f"   - home_score: {home_score_col}")
            print(f"   - away_score: {away_score_col}")
            
            # Construir SELECT solo con columnas que existen
            select_cols = [f"g.{id_column} AS id"]
            
            if home_team_col:
                select_cols.append(f"g.{home_team_col}")
            if away_team_col:
                select_cols.append(f"g.{away_team_col}")
            if date_col:
                select_cols.append(f"g.{date_col}")
            if home_score_col:
                select_cols.append(f"g.{home_score_col}")
            if away_score_col:
                select_cols.append(f"g.{away_score_col}")
            
            if not select_cols:
                raise Exception("No se pudieron mapear columnas válidas")
            
            # No hay tabla teams, así que no hacemos JOINs
            join_clause = ""
            team_select = ""
            
            # Construir query SQL
            sql = f"""
                SELECT {', '.join(select_cols)}{team_select}
                FROM espn.games g
                {join_clause}
                WHERE 1=1
            """
            params = {}
            
            # Agregar filtros dinámicamente (solo con columnas que existen)
            if date_from and date_col:
                sql += f" AND g.{date_col} >= :date_from"
                params['date_from'] = date_from
            if date_to and date_col:
                sql += f" AND g.{date_col} <= :date_to"
                params['date_to'] = date_to
            
            # status no existe en games, así que no se filtra
            
            if team_id and home_team_col and away_team_col:
                # Filtrar por nombre de equipo (ya que no hay IDs)
                sql += f" AND (g.{home_team_col} = :team_id OR g.{away_team_col} = :team_id)"
                params['team_id'] = team_id
            
            # Ordenar
            order_col = date_col if date_col else id_column
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
                
                # Obtener valores de home_team y away_team (son strings en la BD)
                home_team_name = match_dict.get(home_team_col) if home_team_col else None
                away_team_name = match_dict.get(away_team_col) if away_team_col else None
                
                # No hay tabla teams, así que generamos IDs basados en hash del nombre
                def generate_team_id(team_name: Optional[str]) -> Optional[int]:
                    """Generar un ID simple basado en el nombre del equipo"""
                    if not team_name:
                        return None
                    return abs(hash(team_name)) % (10 ** 9)  # ID positivo de hasta 9 dígitos
                
                home_team_id = generate_team_id(home_team_name) if home_team_name else None
                away_team_id = generate_team_id(away_team_name) if away_team_name else None
                
                # No hay información adicional de equipos (abbreviation, city, etc.)
                home_team_abbr = ''
                home_team_city = ''
                home_team_conf = ''
                home_team_div = ''
                away_team_abbr = ''
                away_team_city = ''
                away_team_conf = ''
                away_team_div = ''
                
                # Construir objeto MatchResponse usando solo columnas que existen
                match = {
                    "id": match_dict.get('id'),
                    "espn_id": None,
                    "home_team_id": int(home_team_id) if home_team_id else None,
                    "away_team_id": int(away_team_id) if away_team_id else None,
                    "game_date": None,  # No se incluye la fecha
                    "season": None,  # No existe en games
                    "season_type": None,  # No existe en games
                    "status": None,  # No existe en games
                    "home_score": int(match_dict.get(home_score_col)) if home_score_col and match_dict.get(home_score_col) is not None else None,
                    "away_score": int(match_dict.get(away_score_col)) if away_score_col and match_dict.get(away_score_col) is not None else None,
                    "winner_id": None,
                    "home_odds": None,
                    "away_odds": None,
                    "over_under": None,
                    "created_at": None,
                    "updated_at": None,
                    "home_team": {
                        "id": int(home_team_id) if home_team_id else 0,
                        "name": home_team_name or 'Unknown',
                        "abbreviation": home_team_abbr,
                        "city": home_team_city,
                        "conference": home_team_conf,
                        "division": home_team_div,
                    } if home_team_name else None,
                    "away_team": {
                        "id": int(away_team_id) if away_team_id else 0,
                        "name": away_team_name or 'Unknown',
                        "abbreviation": away_team_abbr,
                        "city": away_team_city,
                        "conference": away_team_conf,
                        "division": away_team_div,
                    } if away_team_name else None,
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
                    game.home_team = self.db.query(Team).filter(Team.team_id == game.home_team_id).first()
                    game.away_team = self.db.query(Team).filter(Team.team_id == game.away_team_id).first()
                    if game.winner_id:
                        game.winner = self.db.query(Team).filter(Team.team_id == game.winner_id).first()
                    
                    result.append(self._game_to_dict(game))
                
                return result
            except Exception as orm_error:
                import traceback
                traceback.print_exc()
                raise Exception(f"Error fetching matches (SQL and ORM failed): {str(e)} | {str(orm_error)}")
    
    async def get_match_by_id(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Get match by ID - trabajando solo con espn.games (sin tabla teams)"""
        try:
            # Obtener columnas reales de la tabla
            columns_dict = self._get_table_columns()
            columns = list(columns_dict.keys())
            
            if not columns:
                raise Exception("No se encontraron columnas en la tabla espn.games")
            
            # Identificar columna de ID - en Neon es 'game_id' (bigint)
            id_column = self._find_column(['game_id', 'id', 'games_id'])
            if not id_column:
                id_column = columns[0]  # Usar la primera columna como fallback
            
            # Mapeo de nombres de columnas esperados a nombres reales en Neon
            # Basado en la estructura real: game_id, fecha, home_team, away_team, etc.
            column_mapping = {
                'id': id_column or 'game_id',  # En Neon es 'game_id'
                'espn_id': None,  # No existe en la estructura real
                'home_team': self._find_column(['home_team']),  # Existe como string
                'away_team': self._find_column(['away_team']),  # Existe como string
                'game_date': self._find_column(['fecha', 'game_date', 'date']),  # En Neon es 'fecha'
                'season': None,  # No existe en la estructura real
                'season_type': None,  # No existe en la estructura real
                'status': None,  # No existe en la estructura real
                'home_score': self._find_column(['home_score', 'home_pts']),  # Existe
                'away_score': self._find_column(['away_score', 'away_pts']),  # Existe
                'winner': None,  # No existe, pero hay 'home_win' (bigint)
                'home_win': self._find_column(['home_win']),  # Existe en Neon
                'home_odds': None,  # No existe en games, está en odds
                'away_odds': None,  # No existe en games, está en odds
                'over_under': None,  # No existe en games
                'created_at': None,  # No existe en la estructura real
                'updated_at': None,  # No existe en la estructura real
            }
            
            # Construir SELECT con columnas disponibles
            select_cols = []
            # En Neon, la columna de ID es 'game_id', pero la mapeamos como 'id' para compatibilidad
            if column_mapping['id']:
                if column_mapping['id'] == 'game_id':
                    select_cols.append("g.game_id AS id")  # Mapear game_id a id
                elif column_mapping['id'] == 'id':
                    select_cols.append("g.id")
                else:
                    select_cols.append(f"g.{column_mapping['id']} AS id")
            
            # Agregar columnas que existen en la estructura real
            for expected_name, actual_name in column_mapping.items():
                if expected_name != 'id' and actual_name:
                    select_cols.append(f"g.{actual_name}")
            
            # Construir query SQL simple - SIN JOINs con teams
            sql = f"""
                SELECT {', '.join(select_cols)}
                FROM espn.games g
                WHERE g.{id_column} = :match_id
                LIMIT 1
            """
            
            print(f"DEBUG get_match_by_id: SQL Query: {sql}")
            print(f"DEBUG get_match_by_id: match_id={match_id}, id_column={id_column}")
            
            result = self.db.execute(text(sql), {"match_id": match_id})
            row = result.fetchone()
            
            if not row:
                print(f"DEBUG get_match_by_id: No row found for match_id={match_id}")
                return None
            
            # Convertir resultado a dict
            match_dict = dict(row._mapping)
            
            print(f"DEBUG get_match_by_id: Available keys: {list(match_dict.keys())}")
            print(f"DEBUG get_match_by_id: match_dict values: {match_dict}")
            print(f"DEBUG get_match_by_id: column_mapping: {column_mapping}")
            
            # Obtener nombres de equipos directamente de las columnas
            home_team_name = None
            away_team_name = None
            
            # Buscar home_team - intentar múltiples estrategias
            # 1. Usar el mapeo de columnas
            if column_mapping.get('home_team'):
                mapped_col = column_mapping['home_team']
                home_team_name = match_dict.get(mapped_col)
                print(f"DEBUG get_match_by_id: Tried column_mapping['home_team']={mapped_col}, value={home_team_name}")
            
            # 2. Buscar en todas las claves posibles del match_dict
            if not home_team_name:
                possible_keys = ['home_team', 'home_team_id', 'team_home', 'home', 'team_home_name']
                for key in possible_keys:
                    if key in match_dict and match_dict[key] is not None:
                        value = match_dict[key]
                        # Si es string y no está vacío, usarlo
                        if isinstance(value, str) and value.strip():
                            home_team_name = value.strip()
                            print(f"DEBUG get_match_by_id: Found home_team_name from key '{key}': {home_team_name}")
                            break
                        # Si es un número, podría ser un ID, pero lo ignoramos por ahora
                        elif isinstance(value, (int, float)):
                            print(f"DEBUG get_match_by_id: Key '{key}' contains numeric value {value}, skipping")
            
            # 3. Buscar en todas las claves que contengan 'home' o 'team'
            if not home_team_name:
                for key, value in match_dict.items():
                    if value is not None and isinstance(value, str) and value.strip():
                        key_lower = key.lower()
                        if ('home' in key_lower or 'team' in key_lower) and 'away' not in key_lower:
                            # Verificar que no sea un ID numérico
                            if not value.strip().isdigit():
                                home_team_name = value.strip()
                                print(f"DEBUG get_match_by_id: Found home_team_name from key '{key}': {home_team_name}")
                                break
            
            # Buscar away_team - intentar múltiples estrategias
            # 1. Usar el mapeo de columnas
            if column_mapping.get('away_team'):
                mapped_col = column_mapping['away_team']
                away_team_name = match_dict.get(mapped_col)
                print(f"DEBUG get_match_by_id: Tried column_mapping['away_team']={mapped_col}, value={away_team_name}")
            
            # 2. Buscar en todas las claves posibles del match_dict
            if not away_team_name:
                possible_keys = ['away_team', 'away_team_id', 'team_away', 'away', 'team_away_name']
                for key in possible_keys:
                    if key in match_dict and match_dict[key] is not None:
                        value = match_dict[key]
                        # Si es string y no está vacío, usarlo
                        if isinstance(value, str) and value.strip():
                            away_team_name = value.strip()
                            print(f"DEBUG get_match_by_id: Found away_team_name from key '{key}': {away_team_name}")
                            break
                        # Si es un número, podría ser un ID, pero lo ignoramos por ahora
                        elif isinstance(value, (int, float)):
                            print(f"DEBUG get_match_by_id: Key '{key}' contains numeric value {value}, skipping")
            
            # 3. Buscar en todas las claves que contengan 'away' o 'team'
            if not away_team_name:
                for key, value in match_dict.items():
                    if value is not None and isinstance(value, str) and value.strip():
                        key_lower = key.lower()
                        if ('away' in key_lower or ('team' in key_lower and 'home' not in key_lower)):
                            # Verificar que no sea un ID numérico
                            if not value.strip().isdigit():
                                away_team_name = value.strip()
                                print(f"DEBUG get_match_by_id: Found away_team_name from key '{key}': {away_team_name}")
                                break
            
            print(f"DEBUG get_match_by_id: Final - home_team_name={home_team_name}, away_team_name={away_team_name}")
            
            # Generar IDs simples basados en hash del nombre (para compatibilidad con el schema)
            # O usar 0 si no hay nombres
            def generate_team_id(team_name: Optional[str]) -> Optional[int]:
                """Generar un ID simple basado en el nombre del equipo"""
                if not team_name:
                    return None
                # Usar hash simple para generar un ID consistente
                return abs(hash(team_name)) % (10 ** 9)  # ID positivo de hasta 9 dígitos
            
            home_team_id = generate_team_id(home_team_name) if home_team_name else None
            away_team_id = generate_team_id(away_team_name) if away_team_name else None
            
            # Construir objeto MatchResponse
            # En Neon, game_id es bigint, lo mapeamos a 'id'
            game_id_value = match_dict.get('id') or match_dict.get('game_id') or match_dict.get(column_mapping['id'])
            
            match = {
                "id": int(game_id_value) if game_id_value else None,
                "espn_id": None,  # No existe en la estructura real
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "game_date": match_dict.get(column_mapping['game_date']) if column_mapping['game_date'] else None,
                "season": None,  # No existe en la estructura real
                "season_type": None,  # No existe en la estructura real
                "status": None,  # No existe en la estructura real
                "home_score": match_dict.get(column_mapping['home_score']) if column_mapping['home_score'] else None,
                "away_score": match_dict.get(column_mapping['away_score']) if column_mapping['away_score'] else None,
                "winner_id": None,  # No hay tabla teams, pero hay home_win (bigint)
                "home_odds": None,  # No existe en games, está en odds
                "away_odds": None,  # No existe en games, está en odds
                "over_under": None,  # No existe en games
                "created_at": None,  # No existe en la estructura real
                "updated_at": None,  # No existe en la estructura real
                "home_team": {
                    "id": home_team_id or 0,
                    "name": home_team_name or 'Unknown',
                    "abbreviation": "",  # No disponible sin tabla teams
                    "city": "",  # No disponible sin tabla teams
                    "conference": "",  # No disponible sin tabla teams
                    "division": "",  # No disponible sin tabla teams
                } if home_team_name else None,
                "away_team": {
                    "id": away_team_id or 0,
                    "name": away_team_name or 'Unknown',
                    "abbreviation": "",  # No disponible sin tabla teams
                    "city": "",  # No disponible sin tabla teams
                    "conference": "",  # No disponible sin tabla teams
                    "division": "",  # No disponible sin tabla teams
                } if away_team_name else None,
                "winner": None,
            }
            
            return match
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
        """Get all teams - NO DISPONIBLE sin tabla espn.teams"""
        # No hay tabla teams, retornar lista vacía
        return []
    
    async def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """Get team by ID - crea un objeto Team simple ya que no hay tabla teams"""
        # Como no hay tabla teams, creamos un objeto Team simple
        # El ID es un hash del nombre, así que no podemos hacer lookup inverso
        # Retornamos un objeto Team con información mínima
        from app.models.team import Team
        
        # Crear un objeto Team simple con el ID proporcionado
        # Nota: No podemos obtener el nombre real sin la tabla teams
        team = Team()
        team.team_id = team_id
        team.name = f"Team {team_id}"  # Nombre genérico
        team.abbreviation = ""
        team.city = ""
        team.conference = ""
        team.division = ""
        return team
