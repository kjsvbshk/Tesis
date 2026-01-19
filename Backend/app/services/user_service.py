"""
User service for business logic
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from app.models.user_accounts import UserAccount, Client, Administrator, Operator
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth_service import get_password_hash

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_user_by_id(self, user_id: int) -> Optional[UserAccount]:
        """Get user account by ID"""
        return self.db.query(UserAccount).filter(UserAccount.id == user_id).first()
    
    async def get_user_by_username(self, username: str) -> Optional[UserAccount]:
        """Get user account by username"""
        return self.db.query(UserAccount).filter(UserAccount.username == username).first()
    
    async def get_user_by_email(self, email: str) -> Optional[UserAccount]:
        """Get user account by email"""
        return self.db.query(UserAccount).filter(UserAccount.email == email).first()
    
    async def get_all_users(self, limit: int = 50, offset: int = 0) -> List[UserAccount]:
        """Get all user accounts with pagination"""
        return self.db.query(UserAccount).offset(offset).limit(limit).all()
    
    async def get_client_by_user_id(self, user_id: int) -> Optional[Client]:
        """Get client record for a user account"""
        return self.db.query(Client).filter(Client.user_account_id == user_id).first()
    
    async def create_user(self, user: UserCreate) -> UserAccount:
        """Create a new user - siempre como cliente por defecto"""
        # Verificar si ya existe
        existing = await self.get_user_by_username(user.username)
        if existing:
            raise ValueError("Username already exists")
        
        existing_email = await self.get_user_by_email(user.email)
        if existing_email:
            raise ValueError("Email already exists")
        
        # Obtener rol de cliente
        client_role = self.db.query(Role).filter(Role.code == 'client').first()
        if not client_role:
            # Si no existe, crear el rol
            client_role = Role(code='client', name='Cliente', description='Usuario que puede realizar apuestas')
            self.db.add(client_role)
            self.db.commit()
            self.db.refresh(client_role)
        
        # Crear cuenta de usuario
        hashed_password = get_password_hash(user.password)
        user_account = UserAccount(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            is_active=True
        )
        self.db.add(user_account)
        self.db.flush()  # Para obtener el ID
        
        # Crear registro de cliente
        client = Client(
            user_account_id=user_account.id,
            role_id=client_role.id,
            credits=1000.0  # Initial credits
        )
        self.db.add(client)
        self.db.commit()
        self.db.refresh(user_account)
        return user_account
    
    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[UserAccount]:
        """Update user account information"""
        user_account = await self.get_user_by_id(user_id)
        if not user_account:
            return None
        
        # Separate UserAccount fields from Client fields
        user_account_fields = {'username', 'email', 'rol', 'credits'}
        client_fields = {'first_name', 'last_name', 'phone', 'date_of_birth'}
        
        update_data = user_update.dict(exclude_unset=True, exclude={'password', 'birth_date'})
        
        # Handle birth_date mapping (frontend sends birth_date, backend uses date_of_birth)
        if user_update.birth_date:
            from datetime import datetime
            try:
                # Parse the date string from frontend
                date_obj = datetime.strptime(user_update.birth_date, '%Y-%m-%d').date()
                update_data['date_of_birth'] = date_obj
            except (ValueError, TypeError):
                pass  # Invalid date format, skip
        
        # Update UserAccount fields
        for field, value in update_data.items():
            if field in user_account_fields and hasattr(user_account, field):
                setattr(user_account, field, value)
        
        # Update Client fields if user is a client
        client = await self.get_client_by_user_id(user_id)
        if client:
            for field, value in update_data.items():
                if field in client_fields and hasattr(client, field):
                    setattr(client, field, value)
        
        # Note: Password changes are handled in a separate endpoint (/users/me/password)
        # Do not update password here
        
        self.db.commit()
        self.db.refresh(user_account)
        return user_account
    
    async def add_credits(self, user_id: int, amount: float) -> bool:
        """Add credits to client account"""
        client = await self.get_client_by_user_id(user_id)
        if not client:
            return False
        
        # Convertir amount a Decimal para operar con client.credits (que es Numeric/Decimal)
        amount_decimal = Decimal(str(amount))
        client.credits += amount_decimal
        self.db.commit()
        return True
    
    async def deduct_credits(self, user_id: int, amount: float) -> bool:
        """Deduct credits from client account"""
        client = await self.get_client_by_user_id(user_id)
        if not client:
            return False
        
        # Convertir amount a Decimal para operar con client.credits (que es Numeric/Decimal)
        amount_decimal = Decimal(str(amount))
        if client.credits < amount_decimal:
            return False
        
        client.credits -= amount_decimal
        self.db.commit()
        return True
    
    async def get_user_credits(self, user_id: int) -> Optional[float]:
        """Get credits for a user (if they are a client)"""
        client = await self.get_client_by_user_id(user_id)
        if not client:
            return None
        return float(client.credits)
    
    async def get_user_role_code(self, user_id: int) -> Optional[str]:
        """Get user role code (client, administrator, operator)"""
        # Check if user is a client
        client = await self.get_client_by_user_id(user_id)
        if client and client.role:
            return client.role.code
        
        # Check if user is an administrator
        administrator = self.db.query(Administrator).filter(Administrator.user_account_id == user_id).first()
        if administrator and administrator.role:
            return administrator.role.code
        
        # Check if user is an operator
        operator = self.db.query(Operator).filter(Operator.user_account_id == user_id).first()
        if operator and operator.role:
            return operator.role.code
        
        return None
