"""
User service for business logic
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth_service import get_password_hash

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    async def get_all_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        """Get all users with pagination"""
        return self.db.query(User).offset(offset).limit(limit).all()
    
    async def create_user(self, user: UserCreate) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            credits=1000.0  # Initial credits
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user information"""
        db_user = await self.get_user_by_id(user_id)
        if not db_user:
            return None
        
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    async def add_credits(self, user_id: int, amount: float) -> Optional[User]:
        """Add credits to user account"""
        db_user = await self.get_user_by_id(user_id)
        if not db_user:
            return None
        
        db_user.credits += amount
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    async def deduct_credits(self, user_id: int, amount: float) -> bool:
        """Deduct credits from user account"""
        db_user = await self.get_user_by_id(user_id)
        if not db_user or db_user.credits < amount:
            return False
        
        db_user.credits -= amount
        self.db.commit()
        return True
