"""
Transaction model for credit management
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase
import enum

class TransactionType(str, enum.Enum):
    """Transaction types"""
    BET_PLACED = "bet_placed"
    BET_WON = "bet_won"
    BET_LOST = "bet_lost"
    CREDIT_PURCHASE = "credit_purchase"
    ADMIN_ADJUSTMENT = "admin_adjustment"

class Transaction(SysBase):
    """Transaction model for credit tracking"""
    
    __tablename__ = "transactions"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app.user_accounts.id"), nullable=False)
    bet_id = Column(Integer, nullable=True)  # Reference to espn.bets.id (no FK constraint due to cross-schema)
    
    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)  # Positive for credits added, negative for credits spent
    balance_before = Column(Float, nullable=False)  # User's balance before transaction
    balance_after = Column(Float, nullable=False)  # User's balance after transaction
    description = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("UserAccount")
    # Note: bet_id references espn.bets.id, but we don't have a relationship
    # because it's in a different schema and we can't have cross-schema relationships
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, type={self.transaction_type}, amount={self.amount})>"
