"""
Bets API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_sys_db
from app.models.bet import Bet, BetType, BetStatus
from app.schemas.bet import BetResponse, BetCreate, BetUpdate
from app.services.bet_service import BetService
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[BetResponse])
async def get_user_bets(
    status: Optional[BetStatus] = Query(None, description="Filter by bet status"),
    limit: int = Query(50, description="Number of bets to return"),
    offset: int = Query(0, description="Number of bets to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get current user's bets"""
    try:
        bet_service = BetService(db)
        bets = await bet_service.get_user_bets(
            user_id=current_user.id,
            status=status,
            limit=limit,
            offset=offset
        )
        return bets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bets: {str(e)}")

@router.post("/", response_model=BetResponse)
async def place_bet(
    bet: BetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Place a new bet"""
    try:
        bet_service = BetService(db)
        
        # Check if user has enough credits
        if current_user.credits < bet.bet_amount:
            raise HTTPException(
                status_code=400, 
                detail="Insufficient credits for this bet"
            )
        
        # Validate bet amount
        if bet.bet_amount < 1.0 or bet.bet_amount > 100.0:
            raise HTTPException(
                status_code=400,
                detail="Bet amount must be between $1.00 and $100.00"
            )
        
        new_bet = await bet_service.place_bet(bet, current_user.id)
        return new_bet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error placing bet: {str(e)}")

@router.get("/{bet_id}", response_model=BetResponse)
async def get_bet(
    bet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get a specific bet by ID"""
    try:
        bet_service = BetService(db)
        bet = await bet_service.get_bet_by_id(bet_id, current_user.id)
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        return bet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bet: {str(e)}")

@router.put("/{bet_id}", response_model=BetResponse)
async def update_bet(
    bet_id: int,
    bet_update: BetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Update a bet (only if pending)"""
    try:
        bet_service = BetService(db)
        updated_bet = await bet_service.update_bet(bet_id, bet_update, current_user.id)
        if not updated_bet:
            raise HTTPException(status_code=404, detail="Bet not found or cannot be updated")
        return updated_bet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating bet: {str(e)}")

@router.delete("/{bet_id}")
async def cancel_bet(
    bet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Cancel a pending bet"""
    try:
        bet_service = BetService(db)
        success = await bet_service.cancel_bet(bet_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Bet not found or cannot be cancelled")
        return {"message": "Bet cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling bet: {str(e)}")

@router.get("/stats/summary")
async def get_betting_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get user's betting statistics"""
    try:
        bet_service = BetService(db)
        stats = await bet_service.get_user_betting_stats(current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching betting stats: {str(e)}")
