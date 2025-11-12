"""
Matches API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.core.database import get_espn_db
from app.models.game import Game
from app.models.team import Team
from app.schemas.match import MatchResponse, MatchCreate
from app.services.match_service import MatchService

router = APIRouter()

@router.get("/", response_model=List[MatchResponse])
async def get_matches(
    date_from: Optional[date] = Query(None, description="Start date for matches"),
    date_to: Optional[date] = Query(None, description="End date for matches"),
    status: Optional[str] = Query(None, description="Match status: scheduled, in_progress, completed"),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    limit: int = Query(50, description="Number of matches to return"),
    offset: int = Query(0, description="Number of matches to skip"),
    db: Session = Depends(get_espn_db)
):
    """Get NBA matches with optional filters"""
    try:
        match_service = MatchService(db)
        matches = await match_service.get_matches(
            date_from=date_from,
            date_to=date_to,
            status=status,
            team_id=team_id,
            limit=limit,
            offset=offset
        )
        # Convertir dicts a MatchResponse
        return [MatchResponse(**match) for match in matches]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching matches: {str(e)}")

@router.get("/today", response_model=List[MatchResponse])
async def get_today_matches(db: Session = Depends(get_espn_db)):
    """Get today's NBA matches (from 2023-2024 and 2024-2025 seasons)"""
    try:
        match_service = MatchService(db)
        # Buscar partidos de las temporadas 2023-2024 y 2024-2025
        # Rango aproximado: Oct 2023 - Jun 2025
        date_from = date(2023, 10, 1)
        date_to = date(2025, 6, 30)
        matches = await match_service.get_matches(date_from=date_from, date_to=date_to, limit=20)
        return [MatchResponse(**match) for match in matches]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching today's matches: {str(e)}")

@router.get("/upcoming", response_model=List[MatchResponse])
async def get_upcoming_matches(
    days: int = Query(7, description="Number of days ahead to look"),
    db: Session = Depends(get_espn_db)
):
    """Get upcoming NBA matches (from 2023-2024 and 2024-2025 seasons)"""
    try:
        match_service = MatchService(db)
        # Buscar partidos de las temporadas 2023-2024 y 2024-2025
        # Rango aproximado: Oct 2023 - Jun 2025
        date_from = date(2023, 10, 1)
        date_to = date(2025, 6, 30)
        matches = await match_service.get_matches(
            date_from=date_from,
            date_to=date_to,
            status="scheduled",
            limit=50
        )
        return [MatchResponse(**match) for match in matches]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching upcoming matches: {str(e)}")

@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int, db: Session = Depends(get_espn_db)):
    """Get a specific match by ID"""
    try:
        match_service = MatchService(db)
        match = await match_service.get_match_by_id(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        return MatchResponse(**match)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching match: {str(e)}")

@router.post("/", response_model=MatchResponse)
async def create_match(match: MatchCreate, db: Session = Depends(get_espn_db)):
    """Create a new match (admin only)"""
    try:
        match_service = MatchService(db)
        new_match = await match_service.create_match(match)
        return new_match
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating match: {str(e)}")
