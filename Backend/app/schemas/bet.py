"""
Bet Pydantic schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import enum

# Enums para Pydantic schemas (valores válidos de la base de datos)
class BetType(str, enum.Enum):
    """Bet type enum"""
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    OVER_UNDER = "over_under"

class BetStatus(str, enum.Enum):
    """Bet status enum"""
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"

class BetBase(BaseModel):
    game_id: int
    bet_type: BetType
    bet_amount: float
    odds: float
    potential_payout: float

class BetCreate(BetBase):
    selected_team_id: Optional[int] = None
    spread_value: Optional[float] = None
    over_under_value: Optional[float] = None
    is_over: Optional[bool] = None

class BetUpdate(BaseModel):
    bet_amount: Optional[float] = None
    odds: Optional[float] = None
    potential_payout: Optional[float] = None

class BetResponse(BetBase):
    id: int
    user_id: int
    selected_team_id: Optional[int] = None
    spread_value: Optional[float] = None
    over_under_value: Optional[float] = None
    is_over: Optional[bool] = None
    status: BetStatus
    actual_payout: Optional[float] = None
    placed_at: datetime
    settled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Related information
    game: dict  # Will contain game details
    selected_team: Optional[dict] = None  # Will contain team details
    
    class Config:
        from_attributes = True
