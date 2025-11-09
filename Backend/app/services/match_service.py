"""
Match service for business logic
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.models.game import Game
from app.models.team import Team
from app.schemas.match import MatchCreate

class MatchService:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_matches(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[str] = None,
        team_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Game]:
        """Get matches with filters"""
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
        
        return query.offset(offset).limit(limit).all()
    
    async def get_match_by_id(self, match_id: int) -> Optional[Game]:
        """Get match by ID"""
        return self.db.query(Game).filter(Game.id == match_id).first()
    
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
