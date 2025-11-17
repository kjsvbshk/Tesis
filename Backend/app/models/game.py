"""
Game model for NBA games
NOTE: This model reflects the ACTUAL database structure, not an idealized normalized structure.
The games table has home_team and away_team as strings, not foreign keys.
Based on actual database schema inspection.
"""

from sqlalchemy import Column, Integer, String, Float, Date, BigInteger
from app.core.database import EspnBase

class Game(EspnBase):
    """NBA Game model - matches actual database structure"""
    
    __tablename__ = "games"
    __table_args__ = {'schema': 'espn'}
    
    game_id = Column(BigInteger, primary_key=True, index=True)
    fecha = Column(Date, nullable=True)
    home_team = Column(String, nullable=True)  # String, not foreign key
    away_team = Column(String, nullable=True)  # String, not foreign key
    home_score = Column(Float, nullable=True)
    away_score = Column(Float, nullable=True)
    
    # Home team stats
    home_fg_pct = Column(Float, nullable=True)
    home_3p_pct = Column(Float, nullable=True)
    home_ft_pct = Column(Float, nullable=True)
    home_reb = Column(Float, nullable=True)
    home_ast = Column(Float, nullable=True)
    home_stl = Column(Float, nullable=True)
    home_blk = Column(Float, nullable=True)
    home_to = Column(Float, nullable=True)
    home_pf = Column(Float, nullable=True)
    home_pts = Column(Float, nullable=True)
    
    # Away team stats
    away_fg_pct = Column(Float, nullable=True)
    away_3p_pct = Column(Float, nullable=True)
    away_ft_pct = Column(Float, nullable=True)
    away_reb = Column(Float, nullable=True)
    away_ast = Column(Float, nullable=True)
    away_stl = Column(Float, nullable=True)
    away_blk = Column(Float, nullable=True)
    away_to = Column(Float, nullable=True)
    away_pf = Column(Float, nullable=True)
    away_pts = Column(Float, nullable=True)
    
    # Normalized team names
    home_team_normalized = Column(String, nullable=True)
    away_team_normalized = Column(String, nullable=True)
    
    # Game results and differences
    home_win = Column(BigInteger, nullable=True)  # bigint, not boolean
    point_diff = Column(Float, nullable=True)
    net_rating_diff = Column(Float, nullable=True)
    reb_diff = Column(Float, nullable=True)
    ast_diff = Column(Float, nullable=True)
    tov_diff = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<Game(game_id={self.game_id}, {self.away_team} @ {self.home_team}, {self.fecha})>"
