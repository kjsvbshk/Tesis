"""
Users API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
import os
import shutil
import uuid
from pathlib import Path

from app.core.database import get_sys_db
from app.core.config import settings
from app.models.user_accounts import UserAccount, Client
from app.schemas.user import (
    UserResponse, UserCreate, UserUpdate, UserLogin, Token,
    SendVerificationCodeRequest, VerifyCodeRequest, RegisterWithVerificationRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    TwoFactorSetupResponse, TwoFactorVerifyRequest, TwoFactorEnableRequest,
    TwoFactorDisableRequest, TwoFactorStatusResponse,
    AvatarUploadResponse, UserSessionResponse, SessionRevokeRequest
)
from app.services.user_service import UserService
from app.services.auth_service import get_current_user, authenticate_user, create_access_token, get_password_hash, verify_password
from app.services.email_service import EmailService
from app.services.two_factor_service import TwoFactorService
from app.services.session_service import SessionService

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    db: Session = Depends(get_sys_db),
    request: Request = None
):
    """Login user and return JWT token"""
    try:
        # First authenticate user with username and password
        user = await authenticate_user(
            db, 
            user_credentials.username, 
            user_credentials.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Check if 2FA is enabled for this user
        two_factor_service = TwoFactorService(db)
        is_2fa_enabled = await two_factor_service.is_2fa_enabled(user.id)
        
        if is_2fa_enabled:
            # 2FA is enabled, require code
            # At this point, username and password have been verified successfully
            if not user_credentials.two_factor_code:
                # Return 401 with special header to indicate 2FA is required
                # Credentials are correct, but 2FA code is missing
                # This tells the frontend to show the 2FA code input screen
                # The frontend should keep username and password and only ask for 2FA code
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="2FA code is required",
                    headers={"X-Requires-2FA": "true"}
                )
            
            # Verify 2FA code (TOTP or backup code)
            # Both username/password AND 2FA code must be correct to proceed
            if not await two_factor_service.verify_2fa_code(user.id, user_credentials.two_factor_code):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid 2FA code"
                )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        # Create session
        session_service = SessionService(db)
        
        # Extract device info and IP
        device_info = None
        ip_address = None
        user_agent = None
        location = None
        
        if request:
            user_agent = request.headers.get("User-Agent")
            ip_address = request.client.host if request.client else None
            device_info = session_service.extract_device_info(user_agent)
            # Location could be determined from IP using a geolocation service
        
        await session_service.create_session(
            user_id=user.id,
            token=access_token,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            location=location
        )
        
        # Obtener el rol del usuario
        user_service = UserService(db)
        user_role = await user_service.get_user_role_code(user.id)
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User role not found"
            )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "rol": user_role
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback_str = traceback.format_exc()
        print(f"Error in login endpoint: {error_detail}")
        print(f"Traceback: {traceback_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during login: {error_detail}"
        )

@router.post("/send-verification-code")
async def send_verification_code(
    request: SendVerificationCodeRequest,
    db: Session = Depends(get_sys_db)
):
    """Send verification code to email"""
    try:
        email_service = EmailService()
        
        # For password reset, verify email exists
        if request.purpose == 'password_reset':
            user_service = UserService(db)
            existing_email = await user_service.get_user_by_email(request.email)
            if not existing_email:
                # Don't reveal if email exists for security
                return {"message": "If the email exists, a verification code has been sent"}
        
        # Queue email sending task (async via RQ) or use direct async method if RQ unavailable
        from app.services.queue_service import queue_service
        from app.tasks.email_tasks import send_verification_email_task
        
        # If RQ is not available, use direct async method (avoid sync fallback issues)
        if not queue_service.is_available():
            # Use async method directly (no RQ, no sync fallback)
            code = await email_service.send_verification_code(
                email=request.email,
                purpose=request.purpose,
                expires_minutes=15
            )
        else:
            # Generate code first to return it (for development)
            code = email_service.generate_verification_code()
            
            # Queue the email sending task
            job = queue_service.enqueue(
                send_verification_email_task,
                request.email,
                request.purpose,
                15,  # expires_minutes
                queue_name='high'  # High priority for verification emails
            )
        
        return {
            "message": "Verification code sent to email",
            "code": code  # Only in development - remove in production
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending verification code: {str(e)}")

@router.post("/verify-code")
async def verify_code(
    request: VerifyCodeRequest,
    db: Session = Depends(get_sys_db)
):
    """Verify the code"""
    try:
        email_service = EmailService()
        user_service = UserService(db)
        
        # Get email based on purpose
        if request.purpose == 'password_reset':
            if not request.username:
                raise HTTPException(
                    status_code=400,
                    detail="Username is required for password reset"
                )
            # Find user by username and get email
            user_account = await user_service.get_user_by_username(request.username)
            if not user_account:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
            email = user_account.email
        else:
            # For registration, email is required
            if not request.email:
                raise HTTPException(
                    status_code=400,
                    detail="Email is required for registration"
                )
            email = request.email
        
        is_valid = await email_service.verify_code(
            email=email,
            code=request.code,
            purpose=request.purpose
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification code"
            )
        
        return {"message": "Code verified successfully", "verified": True, "email": email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying code: {str(e)}")

@router.post("/register", response_model=UserResponse)
async def register_user(user: RegisterWithVerificationRequest, db: Session = Depends(get_sys_db)):
    """Register a new user - requires email verification"""
    try:
        email_service = EmailService()
        user_service = UserService(db)
        
        # Verify that email has been verified
        is_verified = await email_service.is_code_verified(
            email=user.email,
            purpose='registration'
        )
        
        if not is_verified:
            # Also try to verify the code now if provided
            if user.verification_code:
                verified = await email_service.verify_code(
                    email=user.email,
                    code=user.verification_code,
                    purpose='registration'
                )
                if not verified:
                    raise HTTPException(
                        status_code=400,
                        detail="Email verification required. Please verify your email first."
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Email verification required. Please verify your email first."
                )
        
        # Check if username already exists
        existing_user = await user_service.get_user_by_username(user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Check if email already exists
        existing_email = await user_service.get_user_by_email(user.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user with verified email
        user_create = UserCreate(
            username=user.username,
            email=user.email,
            password=user.password
        )
        new_user_account = await user_service.create_user(user_create)
        
        # Obtener información del cliente y el rol para la respuesta
        client = await user_service.get_client_by_user_id(new_user_account.id)
        user_role = await user_service.get_user_role_code(new_user_account.id)
        if not user_role:
            raise HTTPException(status_code=500, detail="User role not found")
        
        user_dict = {
            "id": new_user_account.id,
            "username": new_user_account.username,
            "email": new_user_account.email,
            "is_active": new_user_account.is_active,
            "credits": float(client.credits) if client else None,
            "rol": user_role,
            "created_at": new_user_account.created_at,
            "updated_at": new_user_account.updated_at,
            "avatar_url": new_user_account.avatar_url,
        }
        return user_dict
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback_str = traceback.format_exc()
        print(f"Error creating user: {error_detail}")
        print(f"Traceback: {traceback_str}")
        raise HTTPException(status_code=500, detail=f"Error creating user: {error_detail}")

@router.post("/logout")
async def logout(current_user: UserAccount = Depends(get_current_user)):
    """Logout user - invalida la sesión del lado del servidor"""
    # Con JWT stateless, técnicamente no hay nada que invalidar en el servidor
    # Pero este endpoint permite:
    # 1. Registrar el logout para auditoría
    # 2. Notificar al cliente que el logout fue exitoso
    # 3. En el futuro, podríamos implementar una blacklist de tokens
    return {
        "message": "Logout successful",
        "username": current_user.username
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get current user information"""
    # Obtener información adicional según el tipo de usuario
    user_service = UserService(db)
    client = await user_service.get_client_by_user_id(current_user.id)
    user_role = await user_service.get_user_role_code(current_user.id)
    if not user_role:
        raise HTTPException(status_code=500, detail="User role not found")
    
    user_dict = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "credits": float(client.credits) if client else None,
        "rol": user_role,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "avatar_url": current_user.avatar_url,
        # Include Client profile fields if user is a client
        "first_name": client.first_name if client else None,
        "last_name": client.last_name if client else None,
        "phone": client.phone if client else None,
        "date_of_birth": client.date_of_birth if client else None,
    }
    return user_dict

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Update current user information - no permite cambiar el rol"""
    try:
        user_service = UserService(db)
        
        # Los usuarios no pueden cambiar su propio rol
        if hasattr(user_update, 'rol') and user_update.rol is not None:
            # Remover el campo rol del update si viene en el request
            update_dict = user_update.dict(exclude_unset=True)
            update_dict.pop('rol', None)
            user_update = UserUpdate(**update_dict)
        
        updated_user = await user_service.update_user(current_user.id, user_update)
        
        # Obtener información del cliente y el rol para la respuesta
        client = await user_service.get_client_by_user_id(updated_user.id)
        user_role = await user_service.get_user_role_code(updated_user.id)
        if not user_role:
            raise HTTPException(status_code=500, detail="User role not found")
        
        user_dict = {
            "id": updated_user.id,
            "username": updated_user.username,
            "email": updated_user.email,
            "is_active": updated_user.is_active,
            "credits": float(client.credits) if client else None,
            "rol": user_role,
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at,
            "avatar_url": updated_user.avatar_url,
            # Include Client profile fields if user is a client
            "first_name": client.first_name if client else None,
            "last_name": client.last_name if client else None,
            "phone": client.phone if client else None,
            "date_of_birth": client.date_of_birth if client else None,
        }
        return user_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@router.put("/me/password")
async def change_password(
    password_data: dict,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Change user password with enhanced security:
    - Password complexity validation
    - Rate limiting (max 5 attempts per hour)
    - Audit logging
    - Email notification (optional)
    """
    try:
        from app.services.auth_service import verify_password, get_password_hash
        from app.services.audit_service import AuditService
        from app.services.cache_service import cache_service
        from datetime import datetime, timedelta
        import re
        
        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        
        if not current_password or not new_password:
            raise HTTPException(status_code=400, detail="current_password and new_password are required")
        
        # Rate limiting: Check attempts in last hour
        rate_limit_key = f"password_change_attempts:{current_user.id}"
        attempts_data = cache_service.get(rate_limit_key, allow_stale=False)
        
        if attempts_data and attempts_data.get("data"):
            attempts = attempts_data["data"].get("count", 0)
            last_attempt = attempts_data["data"].get("last_attempt")
            if attempts >= 5:
                if last_attempt:
                    last_attempt_time = datetime.fromisoformat(last_attempt)
                    time_since_last = datetime.utcnow() - last_attempt_time.replace(tzinfo=None)
                    if time_since_last < timedelta(hours=1):
                        remaining_minutes = int((timedelta(hours=1) - time_since_last).total_seconds() / 60)
                        raise HTTPException(
                            status_code=429,
                            detail=f"Too many password change attempts. Please try again in {remaining_minutes} minutes."
                        )
                    else:
                        # Reset counter after 1 hour
                        cache_service.set(rate_limit_key, {"count": 0, "last_attempt": None}, ttl_seconds=3600)
        
        # Enhanced password validation
        if len(new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New password must be at least 8 characters long"
            )
        
        # Check password complexity
        has_upper = bool(re.search(r'[A-Z]', new_password))
        has_lower = bool(re.search(r'[a-z]', new_password))
        has_digit = bool(re.search(r'\d', new_password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password))
        
        complexity_score = sum([has_upper, has_lower, has_digit, has_special])
        if complexity_score < 3:
            raise HTTPException(
                status_code=400,
                detail="New password must contain at least 3 of the following: uppercase letter, lowercase letter, digit, special character"
            )
        
        # Check if new password is same as current
        if verify_password(new_password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="New password must be different from current password"
            )
        
        # Verify current password
        if not verify_password(current_password, current_user.hashed_password):
            # Increment rate limit counter
            if attempts_data and attempts_data.get("data"):
                attempts = attempts_data["data"].get("count", 0) + 1
            else:
                attempts = 1
            
            cache_service.set(
                rate_limit_key,
                {"count": attempts, "last_attempt": datetime.utcnow().isoformat()},
                ttl_seconds=3600
            )
            
            # Log failed attempt
            audit_service = AuditService(db)
            await audit_service.log_action(
                action="password_change_failed",
                actor_user_id=current_user.id,
                resource_type="user",
                resource_id=current_user.id,
                metadata={"reason": "incorrect_current_password"},
                commit=False
            )
            
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        user_service = UserService(db)
        db_user = await user_service.get_user_by_id(current_user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_user.hashed_password = get_password_hash(new_password)
        
        # Log password change
        audit_service = AuditService(db)
        await audit_service.log_action(
            action="password_changed",
            actor_user_id=current_user.id,
            resource_type="user",
            resource_id=current_user.id,
            metadata={"password_changed_at": datetime.utcnow().isoformat()},
            commit=False
        )
        
        db.commit()
        db.refresh(db_user)
        
        # Reset rate limit on success
        cache_service.delete(rate_limit_key)
        
        # Send email notification (optional, if email service is configured)
        try:
            from app.services.email_service import EmailService
            email_service = EmailService()
            # Note: Email notification for password change could be added here
            # await email_service.send_password_change_notification(current_user.email)
        except:
            pass  # Email notification is optional
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error changing password: {str(e)}")

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_sys_db)
):
    """Request password reset - sends verification code to email associated with username"""
    try:
        email_service = EmailService()
        user_service = UserService(db)
        
        # Find user by username and get their email
        user_account = await user_service.get_user_by_username(request.username)
        if not user_account:
            # Don't reveal if username exists for security
            return {"message": "If the username exists, a verification code has been sent to the associated email"}
        
        email = user_account.email
        
        # Queue email sending task (async via RQ) or use direct async method if RQ unavailable
        from app.services.queue_service import queue_service
        from app.tasks.email_tasks import send_verification_email_task
        
        # Always use async method directly to ensure email is sent
        # RQ can be unreliable in some environments, so we'll use direct async method
        code = await email_service.send_verification_code(
            email=email,
            purpose='password_reset',
            expires_minutes=15
        )
        
        # Optionally also queue it for background processing if RQ is available
        # This ensures the email is sent even if RQ fails
        if queue_service.is_available():
            try:
                queue_service.enqueue(
                    send_verification_email_task,
                    email,
                    'password_reset',
                    15,  # expires_minutes
                    queue_name='high'
                )
            except Exception as e:
                # If queuing fails, that's okay - we already sent it directly
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to queue email task, but email was sent directly: {e}")
        
        return {
            "message": "If the username exists, a verification code has been sent to the associated email",
            "code": code,  # Only in development - remove in production
            "email": email  # Only in development - remove in production
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing password reset request: {str(e)}")

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_sys_db)
):
    """Reset password after code verification"""
    try:
        email_service = EmailService()
        user_service = UserService(db)
        
        # Find user by username and get their email
        user_account = await user_service.get_user_by_username(request.username)
        if not user_account:
            raise HTTPException(status_code=404, detail="User not found")
        
        email = user_account.email
        
        # Verify the code (allows re-verification if already verified with correct code)
        is_verified = await email_service.verify_code(
            email=email,
            code=request.code,
            purpose='password_reset'
        )
        
        if not is_verified:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification code"
            )
        
        # Validate new password
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=400,
                detail="New password must be at least 6 characters long"
            )
        
        # Update password
        user_account.hashed_password = get_password_hash(request.new_password)
        db.commit()
        db.refresh(user_account)
        
        return {"message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting password: {str(e)}")

@router.get("/me/permissions")
async def get_my_permissions(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get current user's permissions"""
    try:
        from app.core.authorization import get_user_permissions, get_user_scopes
        from app.services.role_service import RoleService
        
        # Obtener permisos y scopes del usuario
        permissions = get_user_permissions(db, current_user.id)
        scopes = get_user_scopes(db, current_user.id)
        
        # Obtener roles del usuario
        role_service = RoleService(db)
        roles = await role_service.get_user_roles(current_user.id)
        
        return {
            "user_id": current_user.id,
            "username": current_user.username,
            "roles": [{"id": r.id, "code": r.code, "name": r.name} for r in roles],
            "permissions": permissions,
            "scopes": scopes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching permissions: {str(e)}")

@router.get("/credits")
async def get_user_credits(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get current user's credit balance"""
    user_service = UserService(db)
    credits = await user_service.get_user_credits(current_user.id)
    
    if credits is None:
        raise HTTPException(status_code=404, detail="User is not a client or has no credits")
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "credits": credits
    }

@router.post("/credits/add")
async def add_credits(
    amount: float,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Add credits to user account (for testing purposes)"""
    try:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        user_service = UserService(db)
        success = await user_service.add_credits(current_user.id, amount)
        
        if not success:
            raise HTTPException(status_code=404, detail="User is not a client")
        
        new_balance = await user_service.get_user_credits(current_user.id)
        
        return {
            "message": f"Added ${amount} credits to your account",
            "new_balance": new_balance
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding credits: {str(e)}")

@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_sys_db)
):
    """Get all users (admin only - for now, no auth required for demo)"""
    try:
        user_service = UserService(db)
        users = await user_service.get_all_users(limit=limit, offset=offset)
        
        # Construir respuestas con todos los campos requeridos
        result = []
        for user_account in users:
            client = await user_service.get_client_by_user_id(user_account.id)
            user_role = await user_service.get_user_role_code(user_account.id)
            if not user_role:
                # Si no tiene rol, saltar este usuario o usar un valor por defecto
                continue
            
            user_dict = {
                "id": user_account.id,
                "username": user_account.username,
                "email": user_account.email,
                "is_active": user_account.is_active,
                "credits": float(client.credits) if client else None,
                "rol": user_role,
                "created_at": user_account.created_at,
                "updated_at": user_account.updated_at,
                "avatar_url": user_account.avatar_url,
            }
            result.append(user_dict)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Deactivate a user account (soft delete - admin only)"""
    try:
        # Check if user has admin permission
        from app.core.authorization import get_user_permissions, has_permission
        user_permissions = get_user_permissions(db, current_user.id)
        if not has_permission("admin:write", user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
        
        # Prevent self-deactivation
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        # Get user info before deactivation for the response
        user_service = UserService(db)
        user_account = await user_service.get_user_by_id(user_id)
        if not user_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        username = user_account.username
        
        # Deactivate user
        success = await user_service.delete_user(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deactivating user"
            )
        
        return {
            "message": f"Usuario '{username}' desactivado correctamente",
            "user_id": user_id,
            "username": username,
            "is_active": False
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deactivating user: {str(e)}")

# ============================================================================
# Two-Factor Authentication Endpoints
# ============================================================================

@router.post("/me/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Setup 2FA for the current user - generates secret and QR code"""
    try:
        two_factor_service = TwoFactorService(db)
        secret, qr_code_url, backup_codes = await two_factor_service.setup_2fa(
            current_user.id,
            current_user.email
        )
        
        return {
            "secret": secret,
            "qr_code_url": qr_code_url,
            "backup_codes": backup_codes
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up 2FA: {str(e)}")

@router.post("/me/2fa/verify")
async def verify_2fa_setup(
    request: TwoFactorVerifyRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Verify 2FA code during setup"""
    try:
        two_factor_service = TwoFactorService(db)
        two_factor = await two_factor_service.get_user_2fa(current_user.id)
        
        if not two_factor:
            raise HTTPException(status_code=400, detail="2FA not set up. Please setup first.")
        
        if two_factor.is_enabled:
            raise HTTPException(status_code=400, detail="2FA is already enabled")
        
        # Verify the code
        if not two_factor_service.verify_totp(two_factor.secret, request.code):
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        return {"message": "Code verified successfully", "verified": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying 2FA: {str(e)}")

@router.post("/me/2fa/enable")
async def enable_2fa(
    request: TwoFactorEnableRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Enable 2FA after verification"""
    try:
        two_factor_service = TwoFactorService(db)
        success = await two_factor_service.verify_and_enable_2fa(current_user.id, request.code)
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        return {"message": "2FA enabled successfully", "enabled": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enabling 2FA: {str(e)}")

@router.post("/me/2fa/disable")
async def disable_2fa(
    request: TwoFactorDisableRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Disable 2FA - requires password confirmation"""
    try:
        # Verify password
        if not verify_password(request.password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid password")
        
        two_factor_service = TwoFactorService(db)
        success = await two_factor_service.disable_2fa(current_user.id)
        
        if not success:
            raise HTTPException(status_code=400, detail="2FA is not enabled")
        
        return {"message": "2FA disabled successfully", "disabled": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disabling 2FA: {str(e)}")

@router.get("/me/2fa/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Get 2FA status for the current user"""
    try:
        two_factor_service = TwoFactorService(db)
        is_setup, is_enabled = await two_factor_service.get_2fa_status(current_user.id)
        
        return {
            "is_setup": is_setup,
            "is_enabled": is_enabled
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching 2FA status: {str(e)}")

# ============================================================================
# Avatar Endpoints
# ============================================================================

@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Upload avatar image for the current user"""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Validate file size (max 2MB)
        file_size = 0
        content = await file.read()
        file_size = len(content)
        if file_size > 2 * 1024 * 1024:  # 2MB
            raise HTTPException(status_code=400, detail="File size exceeds 2MB limit")
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("Backend/uploads/avatars")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        unique_filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        file_path = upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Update user avatar URL
        # Use relative path for serving
        avatar_url = f"/uploads/avatars/{unique_filename}"
        current_user.avatar_url = avatar_url
        db.commit()
        db.refresh(current_user)
        
        # Delete old avatar if exists
        if current_user.avatar_url and current_user.avatar_url != avatar_url:
            old_path = Path(f"Backend{current_user.avatar_url}")
            if old_path.exists():
                old_path.unlink()
        
        return {
            "avatar_url": avatar_url,
            "message": "Avatar uploaded successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading avatar: {str(e)}")

@router.delete("/me/avatar")
async def delete_avatar(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Delete avatar for the current user"""
    try:
        if current_user.avatar_url:
            # Delete file
            file_path = Path(f"Backend{current_user.avatar_url}")
            if file_path.exists():
                file_path.unlink()
            
            # Clear avatar URL
            current_user.avatar_url = None
            db.commit()
        
        return {"message": "Avatar deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting avatar: {str(e)}")

# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.get("/me/sessions", response_model=List[UserSessionResponse])
async def get_user_sessions(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db),
    request: Request = None
):
    """Get all active sessions for the current user"""
    try:
        session_service = SessionService(db)
        sessions = await session_service.get_user_sessions(current_user.id, include_revoked=False)
        
        # Get current session token hash
        current_token_hash = None
        if request:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                current_token_hash = session_service.hash_token(token)
        
        result = []
        for session in sessions:
            result.append({
                "id": session.id,
                "device_info": session.device_info,
                "ip_address": session.ip_address,
                "location": session.location,
                "last_activity": session.last_activity,
                "created_at": session.created_at,
                "is_current": session.token_hash == current_token_hash if current_token_hash else False
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")

@router.post("/me/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: int,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """Revoke a specific session"""
    try:
        session_service = SessionService(db)
        success = await session_service.revoke_session(session_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error revoking session: {str(e)}")

@router.post("/me/sessions/revoke-all")
async def revoke_all_sessions(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db),
    request: Request = None
):
    """Revoke all sessions except the current one"""
    try:
        session_service = SessionService(db)
        
        # Get current token to exclude it
        current_token = None
        if request:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                current_token = auth_header.split(" ")[1]
        
        revoked_count = await session_service.revoke_all_sessions(
            current_user.id,
            exclude_token=current_token
        )
        
        return {
            "message": f"Revoked {revoked_count} session(s)",
            "revoked_count": revoked_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error revoking sessions: {str(e)}")
