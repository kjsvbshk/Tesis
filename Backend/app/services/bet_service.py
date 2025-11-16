"""
Bet service for business logic - Using normalized ESPN schema
"""

from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.models.espn_bet import Bet as EspnBet, BetType, BetStatus, BetSelection, BetResult
from app.models.transaction import Transaction, TransactionType
from app.schemas.bet import BetCreate, BetUpdate
from app.services.user_service import UserService
from app.core.database import get_espn_db

class BetService:
    def __init__(self, sys_db: Session, espn_db: Session = None):
        self.sys_db = sys_db  # Para transacciones y usuarios
        self.espn_db = espn_db or sys_db  # Para apuestas (esquema espn)
        self.user_service = UserService(sys_db)
    
    async def get_user_bets(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[EspnBet]:
        """Get user's bets with filters"""
        query = self.espn_db.query(EspnBet).options(
            joinedload(EspnBet.selection),
            joinedload(EspnBet.result)
        ).filter(EspnBet.user_id == user_id)
        
        if status:
            query = query.filter(EspnBet.bet_status_code == status)
        
        return query.order_by(EspnBet.placed_at.desc()).offset(offset).limit(limit).all()
    
    async def get_bet_by_id(self, bet_id: int, user_id: int) -> Optional[EspnBet]:
        """Get bet by ID (user must own the bet)"""
        return self.espn_db.query(EspnBet).options(
            joinedload(EspnBet.selection),
            joinedload(EspnBet.result)
        ).filter(
            EspnBet.id == bet_id,
            EspnBet.user_id == user_id
        ).first()
    
    async def place_bet(self, bet: BetCreate, user_id: int) -> EspnBet:
        """Place a new bet using normalized schema"""
        # Deduct credits from user
        success = await self.user_service.deduct_credits(user_id, bet.bet_amount)
        if not success:
            raise ValueError("Insufficient credits")
        
        # Convert bet_type enum to string code
        bet_type_code = bet.bet_type.value if hasattr(bet.bet_type, 'value') else str(bet.bet_type)
        
        # Map selected_team_id if it's provided
        # The frontend may send IDs that don't match our team_id (could be ESPN IDs or hash-generated IDs)
        # We need to map them to the correct team_id from the game
        mapped_team_id = None
        if bet.selected_team_id:
            # Get the game to find the correct team_id
            from app.models.game import Game
            from app.models.team import Team
            game = self.espn_db.query(Game).filter(Game.game_id == bet.game_id).first()
            if not game:
                raise ValueError(f"Game {bet.game_id} not found")
            
            # Check if the selected_team_id is already a valid team_id from our teams table
            team = self.espn_db.query(Team).filter(Team.team_id == bet.selected_team_id).first()
            if team:
                # It's already a valid team_id, verify it belongs to this game
                if bet.selected_team_id == game.home_team_id or bet.selected_team_id == game.away_team_id:
                    mapped_team_id = bet.selected_team_id
                else:
                    raise ValueError(f"Team {bet.selected_team_id} is not part of game {bet.game_id}")
            else:
                # The selected_team_id is not a valid team_id in our teams table
                # It might be an ESPN ID or a hash-generated ID from the match service
                # For moneyline bets, we need to determine if it's home or away
                # Since we can't match ESPN IDs directly, we'll check if it matches the game's team_ids
                # (which might have been returned as hash-generated IDs in the match response)
                if bet.selected_team_id == game.home_team_id or bet.selected_team_id == game.away_team_id:
                    # The ID matches one of the game's team_ids (even if it's a hash-generated ID)
                    # But we need to use the actual team_id from the teams table
                    # So we'll use the game's home_team_id or away_team_id directly
                    mapped_team_id = game.home_team_id if bet.selected_team_id == game.home_team_id else game.away_team_id
                else:
                    # The ID doesn't match either team_id from the game
                    # This shouldn't happen if the frontend is sending the correct IDs from the match response
                    # But if it does, we'll try to determine based on the bet type
                    # For moneyline bets, we can't determine home/away from an invalid ID
                    # So we'll raise an error
                    raise ValueError(
                        f"Invalid team_id: {bet.selected_team_id}. "
                        f"The team_id must match one of the game's teams. "
                        f"Game {bet.game_id} has home_team_id={game.home_team_id} and away_team_id={game.away_team_id}."
                    )
        
        # Create bet record in espn schema
        db_bet = EspnBet(
            user_id=user_id,
            game_id=bet.game_id,
            bet_type_code=bet_type_code,
            bet_status_code='pending',
            bet_amount=Decimal(str(bet.bet_amount)),
            odds_value=Decimal(str(bet.odds)),
            potential_payout=Decimal(str(bet.potential_payout)),
            odds_id=None  # Puede ser None si no hay referencia a game_odds
        )
        self.espn_db.add(db_bet)
        self.espn_db.flush()  # Para obtener el ID
        
        # Create bet selection if needed
        if mapped_team_id or bet.spread_value or bet.over_under_value is not None:
            bet_selection = BetSelection(
                bet_id=db_bet.id,
                selected_team_id=mapped_team_id,
                spread_value=Decimal(str(bet.spread_value)) if bet.spread_value else None,
                over_under_value=Decimal(str(bet.over_under_value)) if bet.over_under_value else None,
                is_over=bet.is_over
            )
            self.espn_db.add(bet_selection)
        
        self.espn_db.commit()
        self.espn_db.refresh(db_bet)
        
        # Create transaction record in app schema
        user_credits = await self.user_service.get_user_credits(user_id)
        transaction = Transaction(
            user_id=user_id,
            bet_id=db_bet.id,
            transaction_type=TransactionType.BET_PLACED,
            amount=-bet.bet_amount,
            balance_before=(user_credits or 0) + bet.bet_amount,
            balance_after=user_credits or 0,
            description=f"Bet placed: {bet_type_code} for ${bet.bet_amount}"
        )
        self.sys_db.add(transaction)
        self.sys_db.commit()
        
        return db_bet
    
    async def update_bet(self, bet_id: int, bet_update: BetUpdate, user_id: int) -> Optional[EspnBet]:
        """Update a bet (only if pending)"""
        db_bet = await self.get_bet_by_id(bet_id, user_id)
        if not db_bet or db_bet.bet_status_code != 'pending':
            return None
        
        update_data = bet_update.dict(exclude_unset=True)
        if 'bet_amount' in update_data:
            db_bet.bet_amount = Decimal(str(update_data['bet_amount']))
        if 'odds' in update_data:
            db_bet.odds_value = Decimal(str(update_data['odds']))
        if 'potential_payout' in update_data:
            db_bet.potential_payout = Decimal(str(update_data['potential_payout']))
        
        self.espn_db.commit()
        self.espn_db.refresh(db_bet)
        return db_bet
    
    async def cancel_bet(self, bet_id: int, user_id: int) -> bool:
        """Cancel a pending bet"""
        db_bet = await self.get_bet_by_id(bet_id, user_id)
        if not db_bet or db_bet.bet_status_code != 'pending':
            return False
        
        # Get current credits before refund
        user_credits_before = await self.user_service.get_user_credits(user_id) or 0
        
        # Refund credits
        bet_amount = float(db_bet.bet_amount)
        await self.user_service.add_credits(user_id, bet_amount)
        
        # Get credits after refund
        user_credits_after = await self.user_service.get_user_credits(user_id) or 0
        
        # Update bet status
        db_bet.bet_status_code = 'cancelled'
        db_bet.settled_at = datetime.utcnow()
        self.espn_db.commit()
        
        # Create refund transaction (using ADMIN_ADJUSTMENT for refunds since there's no specific refund type)
        transaction = Transaction(
            user_id=user_id,
            bet_id=bet_id,
            transaction_type=TransactionType.ADMIN_ADJUSTMENT,  # Using admin adjustment for refunds
            amount=bet_amount,
            balance_before=user_credits_before,
            balance_after=user_credits_after,
            description=f"Bet cancelled: refund of ${bet_amount}"
        )
        self.sys_db.add(transaction)
        self.sys_db.commit()
        
        return True
    
    async def settle_bet(self, bet_id: int, won: bool) -> bool:
        """Settle a bet (admin function)"""
        db_bet = self.espn_db.query(EspnBet).filter(EspnBet.id == bet_id).first()
        if not db_bet or db_bet.bet_status_code != 'pending':
            return False
        
        # Get current credits before settlement
        user_credits_before = await self.user_service.get_user_credits(db_bet.user_id) or 0
        
        if won:
            db_bet.bet_status_code = 'won'
            payout = float(db_bet.potential_payout)
            # Add winnings to user account
            await self.user_service.add_credits(db_bet.user_id, payout)
            
            # Get credits after adding winnings
            user_credits_after = await self.user_service.get_user_credits(db_bet.user_id) or 0
            
            # Create or update bet result
            bet_result = self.espn_db.query(BetResult).filter(BetResult.bet_id == bet_id).first()
            if not bet_result:
                bet_result = BetResult(bet_id=bet_id, actual_payout=Decimal(str(payout)))
                self.espn_db.add(bet_result)
            else:
                bet_result.actual_payout = Decimal(str(payout))
            
            # Create transaction for bet won
            transaction = Transaction(
                user_id=db_bet.user_id,
                bet_id=bet_id,
                transaction_type=TransactionType.BET_WON,
                amount=payout,
                balance_before=user_credits_before,
                balance_after=user_credits_after,
                description=f"Bet won: payout of ${payout}"
            )
            self.sys_db.add(transaction)
        else:
            db_bet.bet_status_code = 'lost'
            # Create or update bet result
            bet_result = self.espn_db.query(BetResult).filter(BetResult.bet_id == bet_id).first()
            if not bet_result:
                bet_result = BetResult(bet_id=bet_id, actual_payout=Decimal('0'))
                self.espn_db.add(bet_result)
            else:
                bet_result.actual_payout = Decimal('0')
            
            # Create transaction for bet lost (no credits added, just record)
            transaction = Transaction(
                user_id=db_bet.user_id,
                bet_id=bet_id,
                transaction_type=TransactionType.BET_LOST,
                amount=0.0,
                balance_before=user_credits_before,
                balance_after=user_credits_before,  # No change in balance
                description=f"Bet lost: no payout"
            )
            self.sys_db.add(transaction)
        
        db_bet.settled_at = datetime.utcnow()
        self.espn_db.commit()
        self.sys_db.commit()
        
        return True
    
    async def get_user_betting_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's betting statistics"""
        # Cargar las apuestas con la relación result para evitar N+1 queries
        bets = self.espn_db.query(EspnBet).options(
            joinedload(EspnBet.result)
        ).filter(EspnBet.user_id == user_id).all()
        
        total_bets = len(bets)
        won_bets = len([b for b in bets if b.bet_status_code == 'won'])
        lost_bets = len([b for b in bets if b.bet_status_code == 'lost'])
        pending_bets = len([b for b in bets if b.bet_status_code == 'pending'])
        
        total_wagered = sum(float(b.bet_amount) for b in bets)
        
        # Get actual payouts from BetResult
        total_won = 0.0
        for bet in bets:
            if bet.bet_status_code == 'won' and bet.result:
                total_won += float(bet.result.actual_payout or 0)
        
        win_rate = (won_bets / (won_bets + lost_bets)) * 100 if (won_bets + lost_bets) > 0 else 0
        roi = ((total_won - total_wagered) / total_wagered) * 100 if total_wagered > 0 else 0
        
        return {
            "total_bets": total_bets,
            "won_bets": won_bets,
            "lost_bets": lost_bets,
            "pending_bets": pending_bets,
            "win_rate": round(win_rate, 2),
            "total_wagered": round(total_wagered, 2),
            "total_won": round(total_won, 2),
            "roi": round(roi, 2)
        }
