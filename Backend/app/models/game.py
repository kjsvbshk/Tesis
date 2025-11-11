"""
Game model for NBA games
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import EspnBase

class Game(EspnBase):
    """NBA Game model"""
    
    __tablename__ = "games"
    __table_args__ = {'schema': 'espn'}
    
    id = Column(Integer, primary_key=True, index=True)
    espn_id = Column(String(50), unique=True, nullable=True)  # ESPN game ID
    home_team_id = Column(Integer, ForeignKey("espn.teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("espn.teams.id"), nullable=False)
    game_date = Column(DateTime(timezone=True), nullable=False)
    season = Column(String(10), nullable=False)  # e.g., "2023-24"
    season_type = Column(String(20), nullable=False)  # "regular", "playoffs"
    status = Column(String(20), nullable=False)  # "scheduled", "in_progress", "completed"
    
    # Game results (filled after game completion)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    winner_id = Column(Integer, ForeignKey("espn.teams.id"), nullable=True)
    
    # Betting odds (if available)
    home_odds = Column(Float, nullable=True)  # Decimal odds
    away_odds = Column(Float, nullable=True)  # Decimal odds
    over_under = Column(Float, nullable=True)  # Total points line
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    winner = relationship("Team", foreign_keys=[winner_id])
    
    def __repr__(self):
        return f"<Game(id={self.id}, {self.away_team.name} @ {self.home_team.name}, {self.game_date})>"
