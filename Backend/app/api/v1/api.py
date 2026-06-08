"""
API v1 router configuration
"""

from fastapi import APIRouter
from app.api.v1.endpoints import matches, bets, users, predictions, admin, requests, search, health

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])
api_router.include_router(bets.router, prefix="/bets", tags=["bets"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(predictions.router, prefix="/predict", tags=["predictions"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(requests.router, prefix="/requests", tags=["requests"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
