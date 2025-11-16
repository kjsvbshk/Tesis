"""
Normalized Bet models for espn schema (3FN)
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import EspnBase

# ============================================================================
# Catálogos (Normalización de Enums)
# ============================================================================

class BetType(EspnBase):
    """Bet type catalog"""
    
    __tablename__ = "bet_types"
    __table_args__ = {'schema': 'espn'}
    
    code = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Relationships
    bets = relationship("Bet", back_populates="bet_type")
    
    def __repr__(self):
        return f"<BetType(code='{self.code}', name='{self.name}')>"


class BetStatus(EspnBase):
    """Bet status catalog"""
    
    __tablename__ = "bet_statuses"
    __table_args__ = {'schema': 'espn'}
    
    code = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Relationships
    bets = relationship("Bet", back_populates="bet_status")
    
    def __repr__(self):
        return f"<BetStatus(code='{self.code}', name='{self.name}')>"


# ============================================================================
# Tabla Principal de Apuestas
# ============================================================================

class Bet(EspnBase):
    """Normalized Bet model (3FN)"""
    
    __tablename__ = "bets"
    __table_args__ = (
        CheckConstraint('bet_amount > 0', name='chk_bets_amount_positive'),
        CheckConstraint('potential_payout >= bet_amount', name='chk_bets_payout'),
        {'schema': 'espn'},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # FK a app.user_accounts (sin constraint por esquema diferente)
    game_id = Column(Integer, ForeignKey("espn.games.game_id", ondelete="RESTRICT"), nullable=False)
    
    # Bet type and status (normalized)
    bet_type_code = Column(String(20), ForeignKey("espn.bet_types.code", ondelete="RESTRICT"), nullable=False)
    bet_status_code = Column(String(20), ForeignKey("espn.bet_statuses.code", ondelete="RESTRICT"), nullable=False, default='pending')
    
    # Bet amount
    bet_amount = Column(Numeric(10, 2), nullable=False)
    
    # Odds reference (normalized)
    odds_id = Column(Integer, ForeignKey("espn.game_odds.id", ondelete="SET NULL"), nullable=True)
    odds_value = Column(Numeric(10, 4), nullable=False)  # Snapshot para auditoría
    
    # Potential payout (calculable pero guardado para auditoría)
    potential_payout = Column(Numeric(10, 2), nullable=False)
    
    # Timestamps
    placed_at = Column(DateTime(timezone=True), server_default=func.now())
    settled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id])
    bet_type = relationship("BetType", foreign_keys=[bet_type_code], back_populates="bets")
    bet_status = relationship("BetStatus", foreign_keys=[bet_status_code], back_populates="bets")
    odds = relationship("GameOdds", foreign_keys=[odds_id])
    selection = relationship("BetSelection", back_populates="bet", uselist=False)
    result = relationship("BetResult", back_populates="bet", uselist=False)
    
    def __repr__(self):
        return f"<Bet(id={self.id}, user_id={self.user_id}, amount={self.bet_amount}, status={self.bet_status_code})>"


# ============================================================================
# Selecciones de Apuestas
# ============================================================================

class BetSelection(EspnBase):
    """Bet selection details (normalized)"""
    
    __tablename__ = "bet_selections"
    __table_args__ = (
        CheckConstraint(
            """
            (spread_value IS NULL AND over_under_value IS NULL AND is_over IS NULL) OR
            (over_under_value IS NULL AND is_over IS NULL) OR
            (selected_team_id IS NULL AND spread_value IS NULL)
            """,
            name='chk_bet_selections_logic'
        ),
        {'schema': 'espn'},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("espn.bets.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Selection details (conditional based on bet type)
    selected_team_id = Column(Integer, ForeignKey("espn.teams.team_id", ondelete="RESTRICT"), nullable=True)
    spread_value = Column(Numeric(10, 2), nullable=True)  # For spread bets
    over_under_value = Column(Numeric(10, 2), nullable=True)  # For over/under bets
    is_over = Column(Boolean, nullable=True)  # True for over, False for under
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bet = relationship("Bet", foreign_keys=[bet_id], back_populates="selection")
    selected_team = relationship("Team", foreign_keys=[selected_team_id])
    
    def __repr__(self):
        return f"<BetSelection(bet_id={self.bet_id}, team_id={self.selected_team_id})>"


# ============================================================================
# Resultados de Apuestas
# ============================================================================

class BetResult(EspnBase):
    """Bet result details (normalized)"""
    
    __tablename__ = "bet_results"
    __table_args__ = (
        CheckConstraint('actual_payout >= 0', name='chk_bet_results_payout'),
        {'schema': 'espn'},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("espn.bets.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Result details
    actual_payout = Column(Numeric(10, 2), nullable=True)  # Actual amount won
    result_notes = Column(Text, nullable=True)  # Additional notes
    
    # Timestamps
    settled_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bet = relationship("Bet", foreign_keys=[bet_id], back_populates="result")
    
    def __repr__(self):
        return f"<BetResult(bet_id={self.bet_id}, payout={self.actual_payout})>"


# ============================================================================
# Odds de Partidos (Normalizada)
# ============================================================================

class GameOdds(EspnBase):
    """Game odds (normalized, supports multiple providers and snapshots)"""
    
    __tablename__ = "game_odds"
    __table_args__ = (
        CheckConstraint(
            "odds_type IN ('moneyline_home', 'moneyline_away', 'spread_home', 'spread_away', 'over_under')",
            name='chk_game_odds_type'
        ),
        {'schema': 'espn'},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("espn.games.game_id", ondelete="CASCADE"), nullable=False)
    
    # Odds type
    odds_type = Column(String(20), nullable=False)  # moneyline_home, moneyline_away, spread_home, spread_away, over_under
    
    # Odds values
    odds_value = Column(Numeric(10, 4), nullable=True)  # For moneyline
    line_value = Column(Numeric(10, 2), nullable=True)  # For spread and over/under
    
    # Provider information
    provider = Column(String(50), nullable=True)  # 'espn', 'draftkings', 'fanduel', etc.
    
    # Snapshot time
    snapshot_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    game = relationship("Game", foreign_keys=[game_id])
    bets = relationship("Bet", back_populates="odds")
    
    def __repr__(self):
        return f"<GameOdds(id={self.id}, game_id={self.game_id}, type={self.odds_type}, value={self.odds_value or self.line_value})>"

