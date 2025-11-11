"""
Bet model for virtual betting system
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase
import enum

class BetType(str, enum.Enum):
    """Bet types"""
    MONEYLINE = "moneyline"  # Win/Lose
    SPREAD = "spread"        # Point spread
    OVER_UNDER = "over_under"  # Total points

class BetStatus(str, enum.Enum):
    """Bet status"""
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"

class Bet(SysBase):
    """Virtual Bet model"""
    
    __tablename__ = "bets"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app.users.id"), nullable=False)
    game_id = Column(Integer, nullable=False)  # Referencia a espn.games.id (sin FK porque está en otra BD)
    
    # Bet details
    bet_type = Column(Enum(BetType), nullable=False)
    bet_amount = Column(Float, nullable=False)  # Credits wagered
    odds = Column(Float, nullable=False)  # Decimal odds
    potential_payout = Column(Float, nullable=False)  # Amount to win
    
    # Bet selection
    selected_team_id = Column(Integer, nullable=True)  # Referencia a espn.teams.id (sin FK porque está en otra BD)
    spread_value = Column(Float, nullable=True)  # For spread bets
    over_under_value = Column(Float, nullable=True)  # For over/under bets
    is_over = Column(Boolean, nullable=True)  # True for over, False for under
    
    # Bet status and results
    status = Column(Enum(BetStatus), default=BetStatus.PENDING, nullable=False)
    actual_payout = Column(Float, nullable=True)  # Actual amount won (if any)
    
    # Timestamps
    placed_at = Column(DateTime(timezone=True), server_default=func.now())
    settled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    # game y selected_team no pueden tener relationship porque están en otra base de datos
    # Se manejarán a nivel de aplicación
    
    def __repr__(self):
        return f"<Bet(id={self.id}, user_id={self.user_id}, amount={self.bet_amount}, status={self.status})>"
