"""
Matches API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_espn_db
from app.schemas.match import MatchResponse
from app.services.match_service import MatchService
from app.services.cache_service import cache_service

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
        # Generar clave de caché única basada en los parámetros de búsqueda
        cache_key = cache_service._generate_key(
            "matches",
            "list",
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to) if date_to else None,
            status=status,
            team_id=team_id,
            limit=limit,
            offset=offset
        )
        
        # Función para obtener partidos de la base de datos
        async def fetch_matches():
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
        
        # Obtener del caché o de la base de datos
        # TTL de 5 minutos (300 segundos), stale de 10 minutos (600 segundos)
        matches = await cache_service.get_or_set(
            key=cache_key,
            fetch_func=fetch_matches,
            ttl_seconds=300,  # 5 minutos
            stale_ttl_seconds=600,  # 10 minutos para stale
            allow_stale=True
        )
        
        return matches
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching matches: {str(e)}")

@router.get("/today", response_model=List[MatchResponse])
async def get_today_matches(db: Session = Depends(get_espn_db)):
    """Get NBA matches - returns all available matches"""
    try:
        # Generar clave de caché única para partidos
        cache_key = cache_service._generate_key("matches", "today")
        
        # Función para obtener partidos de la base de datos
        async def fetch_today_matches():
            match_service = MatchService(db)
            # No filtrar por fecha - obtener todos los partidos disponibles
            matches = await match_service.get_matches(limit=50)
            return [MatchResponse(**match) for match in matches]
        
        # Obtener del caché o de la base de datos
        # TTL de 5 minutos (300 segundos), stale de 10 minutos (600 segundos)
        matches = await cache_service.get_or_set(
            key=cache_key,
            fetch_func=fetch_today_matches,
            ttl_seconds=300,  # 5 minutos
            stale_ttl_seconds=600,  # 10 minutos para stale
            allow_stale=True
        )
        
        return matches
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching matches: {str(e)}")

@router.get("/upcoming", response_model=List[MatchResponse])
async def get_upcoming_matches(
    days: int = Query(7, description="Number of days ahead to look (not used, kept for compatibility)"),
    db: Session = Depends(get_espn_db)
):
    """Get NBA matches - returns all available matches"""
    try:
        # Generar clave de caché única para partidos próximos (incluye days en la clave)
        cache_key = cache_service._generate_key("matches", "upcoming", days=days)
        
        # Función para obtener partidos de la base de datos
        async def fetch_upcoming_matches():
            match_service = MatchService(db)
            # No filtrar por fecha - obtener todos los partidos disponibles
            matches = await match_service.get_matches(limit=50)
            return [MatchResponse(**match) for match in matches]
        
        # Obtener del caché o de la base de datos
        # TTL de 5 minutos (300 segundos), stale de 10 minutos (600 segundos)
        matches = await cache_service.get_or_set(
            key=cache_key,
            fetch_func=fetch_upcoming_matches,
            ttl_seconds=300,  # 5 minutos
            stale_ttl_seconds=600,  # 10 minutos para stale
            allow_stale=True
        )
        
        return matches
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching matches: {str(e)}")

@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int, db: Session = Depends(get_espn_db)):
    """Get a specific match by ID"""
    try:
        # Generar clave de caché única para el partido específico
        cache_key = cache_service._generate_key("matches", "by_id", match_id=match_id)
        
        # Función para obtener el partido de la base de datos
        async def fetch_match():
            match_service = MatchService(db)
            match = await match_service.get_match_by_id(match_id)
            if not match:
                raise HTTPException(status_code=404, detail="Match not found")
            return MatchResponse(**match)
        
        # Obtener del caché o de la base de datos
        # TTL de 5 minutos (300 segundos), stale de 10 minutos (600 segundos)
        match = await cache_service.get_or_set(
            key=cache_key,
            fetch_func=fetch_match,
            ttl_seconds=300,  # 5 minutos
            stale_ttl_seconds=600,  # 10 minutos para stale
            allow_stale=True
        )
        
        return match
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching match: {str(e)}")
