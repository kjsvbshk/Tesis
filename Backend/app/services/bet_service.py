"""
Bet service for business logic
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.bet import Bet, BetStatus
from app.models.transaction import Transaction, TransactionType
from app.schemas.bet import BetCreate, BetUpdate
from app.services.user_service import UserService

class BetService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
    
    async def get_user_bets(
        self,
        user_id: int,
        status: Optional[BetStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Bet]:
        """Get user's bets with filters"""
        query = self.db.query(Bet).filter(Bet.user_id == user_id)
        
        if status:
            query = query.filter(Bet.status == status)
        
        return query.order_by(Bet.placed_at.desc()).offset(offset).limit(limit).all()
    
    async def get_bet_by_id(self, bet_id: int, user_id: int) -> Optional[Bet]:
        """Get bet by ID (user must own the bet)"""
        return self.db.query(Bet).filter(
            Bet.id == bet_id,
            Bet.user_id == user_id
        ).first()
    
    async def place_bet(self, bet: BetCreate, user_id: int) -> Bet:
        """Place a new bet"""
        # Deduct credits from user
        success = await self.user_service.deduct_credits(user_id, bet.bet_amount)
        if not success:
            raise ValueError("Insufficient credits")
        
        # Create bet record
        db_bet = Bet(
            user_id=user_id,
            **bet.dict()
        )
        self.db.add(db_bet)
        self.db.commit()
        self.db.refresh(db_bet)
        
        # Create transaction record
        user = await self.user_service.get_user_by_id(user_id)
        transaction = Transaction(
            user_id=user_id,
            bet_id=db_bet.id,
            transaction_type=TransactionType.BET_PLACED,
            amount=-bet.bet_amount,
            balance_before=user.credits + bet.bet_amount,
            balance_after=user.credits,
            description=f"Bet placed: {bet.bet_type} for ${bet.bet_amount}"
        )
        self.db.add(transaction)
        self.db.commit()
        
        return db_bet
    
    async def update_bet(self, bet_id: int, bet_update: BetUpdate, user_id: int) -> Optional[Bet]:
        """Update a bet (only if pending)"""
        db_bet = await self.get_bet_by_id(bet_id, user_id)
        if not db_bet or db_bet.status != BetStatus.PENDING:
            return None
        
        update_data = bet_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_bet, field, value)
        
        self.db.commit()
        self.db.refresh(db_bet)
        return db_bet
    
    async def cancel_bet(self, bet_id: int, user_id: int) -> bool:
        """Cancel a pending bet"""
        db_bet = await self.get_bet_by_id(bet_id, user_id)
        if not db_bet or db_bet.status != BetStatus.PENDING:
            return False
        
        # Refund credits
        await self.user_service.add_credits(user_id, db_bet.bet_amount)
        
        # Update bet status
        db_bet.status = BetStatus.CANCELLED
        db_bet.settled_at = datetime.utcnow()
        
        # Create refund transaction
        user = await self.user_service.get_user_by_id(user_id)
        transaction = Transaction(
            user_id=user_id,
            bet_id=bet_id,
            transaction_type=TransactionType.BET_PLACED,  # Refund
            amount=db_bet.bet_amount,
            balance_before=user.credits - db_bet.bet_amount,
            balance_after=user.credits,
            description=f"Bet cancelled: refund of ${db_bet.bet_amount}"
        )
        self.db.add(transaction)
        self.db.commit()
        
        return True
    
    async def settle_bet(self, bet_id: int, won: bool) -> bool:
        """Settle a bet (admin function)"""
        db_bet = self.db.query(Bet).filter(Bet.id == bet_id).first()
        if not db_bet or db_bet.status != BetStatus.PENDING:
            return False
        
        if won:
            db_bet.status = BetStatus.WON
            db_bet.actual_payout = db_bet.potential_payout
            # Add winnings to user account
            await self.user_service.add_credits(db_bet.user_id, db_bet.potential_payout)
        else:
            db_bet.status = BetStatus.LOST
            db_bet.actual_payout = 0.0
        
        db_bet.settled_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    async def get_user_betting_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's betting statistics"""
        bets = self.db.query(Bet).filter(Bet.user_id == user_id).all()
        
        total_bets = len(bets)
        won_bets = len([b for b in bets if b.status == BetStatus.WON])
        lost_bets = len([b for b in bets if b.status == BetStatus.LOST])
        pending_bets = len([b for b in bets if b.status == BetStatus.PENDING])
        
        total_wagered = sum(b.bet_amount for b in bets)
        total_won = sum(b.actual_payout or 0 for b in bets if b.status == BetStatus.WON)
        
        win_rate = (won_bets / (won_bets + lost_bets)) * 100 if (won_bets + lost_bets) > 0 else 0
        roi = ((total_won - total_wagered) / total_wagered) * 100 if total_wagered > 0 else 0
        
        return {
            "total_bets": total_bets,
            "won_bets": won_bets,
            "lost_bets": lost_bets,
            "pending_bets": pending_bets,
            "win_rate": round(win_rate, 2),
            "total_wagered": total_wagered,
            "total_won": total_won,
            "roi": round(roi, 2)
        }
