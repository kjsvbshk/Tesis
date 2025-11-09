"""
Users API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.services.user_service import UserService
from app.services.auth_service import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        user_service = UserService(db)
        
        # Check if username already exists
        existing_user = await user_service.get_user_by_username(user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Check if email already exists
        existing_email = await user_service.get_user_by_email(user.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        new_user = await user_service.create_user(user)
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(current_user.id, user_update)
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@router.get("/credits")
async def get_user_credits(current_user: User = Depends(get_current_user)):
    """Get current user's credit balance"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "credits": current_user.credits
    }

@router.post("/credits/add")
async def add_credits(
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add credits to user account (for testing purposes)"""
    try:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        user_service = UserService(db)
        updated_user = await user_service.add_credits(current_user.id, amount)
        
        return {
            "message": f"Added ${amount} credits to your account",
            "new_balance": updated_user.credits
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding credits: {str(e)}")

@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all users (admin only - for now, no auth required for demo)"""
    try:
        user_service = UserService(db)
        users = await user_service.get_all_users(limit=limit, offset=offset)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")
