"""
API v1 router configuration
"""

from fastapi import APIRouter
from app.api.v1.endpoints import matches, bets, users, predictions

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])
api_router.include_router(bets.router, prefix="/bets", tags=["bets"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(predictions.router, prefix="/predict", tags=["predictions"])
