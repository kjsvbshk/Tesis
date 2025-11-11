"""
Team statistics model for games
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import EspnBase

class TeamStatsGame(EspnBase):
    """Team statistics for a specific game"""
    
    __tablename__ = "team_stats_game"
    __table_args__ = {'schema': 'espn'}
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("espn.games.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("espn.teams.id"), nullable=False)
    is_home = Column(Boolean, nullable=False)  # True if home team, False if away
    
    # Basic stats
    points = Column(Integer, nullable=True)
    field_goals_made = Column(Integer, nullable=True)
    field_goals_attempted = Column(Integer, nullable=True)
    field_goal_percentage = Column(Float, nullable=True)
    three_pointers_made = Column(Integer, nullable=True)
    three_pointers_attempted = Column(Integer, nullable=True)
    three_point_percentage = Column(Float, nullable=True)
    free_throws_made = Column(Integer, nullable=True)
    free_throws_attempted = Column(Integer, nullable=True)
    free_throw_percentage = Column(Float, nullable=True)
    
    # Advanced stats
    rebounds = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    steals = Column(Integer, nullable=True)
    blocks = Column(Integer, nullable=True)
    turnovers = Column(Integer, nullable=True)
    personal_fouls = Column(Integer, nullable=True)
    
    # Team efficiency
    offensive_rating = Column(Float, nullable=True)
    defensive_rating = Column(Float, nullable=True)
    net_rating = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    game = relationship("Game")
    team = relationship("Team")
    
    def __repr__(self):
        return f"<TeamStatsGame(id={self.id}, game_id={self.game_id}, team_id={self.team_id}, points={self.points})>"
