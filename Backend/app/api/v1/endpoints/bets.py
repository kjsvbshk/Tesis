"""
Bets API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import asyncio

from app.core.database import get_sys_db, get_espn_db
from app.models.bet import Bet, BetType, BetStatus
from app.schemas.bet import BetResponse, BetCreate, BetUpdate
from app.services.bet_service import BetService
from app.services.audit_service import AuditService
from app.services.outbox_service import OutboxService
from app.services.auth_service import get_current_user
from app.services.match_service import MatchService
from app.models.user import User

router = APIRouter()

async def build_bet_response(bet: Bet, espn_db: Session) -> BetResponse:
    """Construir BetResponse con información del juego"""
    # Obtener información del juego
    match_service = MatchService(espn_db)
    game_info = {}
    selected_team_info = None
    
    try:
        game_dict = await match_service.get_match_by_id(bet.game_id)
        if game_dict:
            game_info = game_dict
        else:
            # Si no se puede obtener el juego, crear un dict básico
            game_info = {
                "id": bet.game_id,
                "home_team": None,
                "away_team": None,
                "game_date": None
            }
    except Exception as e:
        # Si no se puede obtener el juego, crear un dict básico
        import traceback
        traceback.print_exc()
        game_info = {
            "id": bet.game_id,
            "home_team": None,
            "away_team": None,
            "game_date": None
        }
    
    # Obtener información del equipo seleccionado si existe
    if bet.selected_team_id:
        try:
            team = await match_service.get_team_by_id(bet.selected_team_id)
            if team:
                selected_team_info = {
                    "id": team.id,
                    "name": team.name,
                    "abbreviation": team.abbreviation,
                    "city": team.city
                }
        except Exception as e:
            import traceback
            traceback.print_exc()
            pass
    
    # Asegurar que game_info nunca sea None
    if not game_info:
        game_info = {
            "id": bet.game_id,
            "home_team": None,
            "away_team": None,
            "game_date": None
        }
    
    # Construir la respuesta
    bet_dict = {
        "id": bet.id,
        "user_id": bet.user_id,
        "game_id": bet.game_id,
        "bet_type": bet.bet_type,
        "bet_amount": bet.bet_amount,
        "odds": bet.odds,
        "potential_payout": bet.potential_payout,
        "selected_team_id": bet.selected_team_id,
        "spread_value": bet.spread_value,
        "over_under_value": bet.over_under_value,
        "is_over": bet.is_over,
        "status": bet.status,
        "actual_payout": bet.actual_payout,
        "placed_at": bet.placed_at,
        "settled_at": bet.settled_at,
        "created_at": bet.created_at,
        "updated_at": bet.updated_at,
        "game": game_info,  # Ya aseguramos que nunca sea None
        "selected_team": selected_team_info
    }
    
    try:
        return BetResponse(**bet_dict)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise ValueError(f"Error constructing BetResponse: {str(e)}")

@router.get("/", response_model=List[BetResponse])
async def get_user_bets(
    status: Optional[BetStatus] = Query(None, description="Filter by bet status"),
    limit: int = Query(50, description="Number of bets to return"),
    offset: int = Query(0, description="Number of bets to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db),
    espn_db: Session = Depends(get_espn_db)
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
        # Construir respuestas con información del juego
        return await asyncio.gather(*[build_bet_response(bet, espn_db) for bet in bets])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bets: {str(e)}")

@router.post("/", response_model=BetResponse)
async def place_bet(
    bet: BetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db),
    espn_db: Session = Depends(get_espn_db)
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
        
        # Registrar en auditoría (RF-09)
        audit_service = AuditService(db)
        await audit_service.log_bet_action(
            action="bet.placed",
            actor_user_id=current_user.id,
            bet_id=new_bet.id,
            after={
                "bet_id": new_bet.id,
                "bet_type": new_bet.bet_type.value if hasattr(new_bet.bet_type, 'value') else str(new_bet.bet_type),
                "bet_amount": new_bet.bet_amount,
                "odds": new_bet.odds,
                "game_id": new_bet.game_id
            },
            commit=True
        )
        
        # Publicar evento en outbox (RF-08)
        outbox_service = OutboxService(db)
        await outbox_service.publish_bet_placed(
            bet_id=new_bet.id,
            user_id=current_user.id,
            bet_data={
                "bet_id": new_bet.id,
                "bet_type": new_bet.bet_type.value if hasattr(new_bet.bet_type, 'value') else str(new_bet.bet_type),
                "bet_amount": new_bet.bet_amount,
                "odds": new_bet.odds,
                "game_id": new_bet.game_id
            },
            commit=True
        )
        
        # Construir respuesta con información del juego
        bet_response = await build_bet_response(new_bet, espn_db)
        # Asegurar que siempre devolvemos un BetResponse válido
        if not isinstance(bet_response, BetResponse):
            raise HTTPException(
                status_code=500, 
                detail=f"Error constructing bet response: expected BetResponse, got {type(bet_response)}"
            )
        return bet_response
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error placing bet: {str(e)}")

@router.get("/{bet_id}", response_model=BetResponse)
async def get_bet(
    bet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db),
    espn_db: Session = Depends(get_espn_db)
):
    """Get a specific bet by ID"""
    try:
        bet_service = BetService(db)
        bet = await bet_service.get_bet_by_id(bet_id, current_user.id)
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        return await build_bet_response(bet, espn_db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bet: {str(e)}")

@router.put("/{bet_id}", response_model=BetResponse)
async def update_bet(
    bet_id: int,
    bet_update: BetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sys_db),
    espn_db: Session = Depends(get_espn_db)
):
    """Update a bet (only if pending)"""
    try:
        bet_service = BetService(db)
        updated_bet = await bet_service.update_bet(bet_id, bet_update, current_user.id)
        if not updated_bet:
            raise HTTPException(status_code=404, detail="Bet not found or cannot be updated")
        return await build_bet_response(updated_bet, espn_db)
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
