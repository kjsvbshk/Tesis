"""
Match Pydantic schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TeamBase(BaseModel):
    id: int
    name: str
    abbreviation: str
    city: str
    conference: str
    division: str

class MatchResponse(BaseModel):
    id: int
    espn_id: Optional[str] = None
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    game_date: Optional[datetime] = None
    season: Optional[str] = None
    season_type: Optional[str] = None
    status: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    winner_id: Optional[int] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    over_under: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Team information
    home_team: Optional[TeamBase] = None
    away_team: Optional[TeamBase] = None
    winner: Optional[TeamBase] = None
    
    class Config:
        from_attributes = True
