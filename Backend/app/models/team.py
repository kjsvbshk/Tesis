"""
Team model for NBA teams
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.core.database import EspnBase

class Team(EspnBase):
    """NBA Team model"""
    
    __tablename__ = "teams"
    __table_args__ = {'schema': 'espn'}
    
    team_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., "Los Angeles Lakers"
    abbreviation = Column(String(10), unique=True, nullable=False)  # e.g., "LAL"
    city = Column(String(50), nullable=False)  # e.g., "Los Angeles"
    conference = Column(String(20), nullable=False)  # "Eastern" or "Western"
    division = Column(String(20), nullable=False)  # e.g., "Pacific"
    logo_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Team(team_id={self.team_id}, name='{self.name}', abbreviation='{self.abbreviation}')>"
