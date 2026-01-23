"""
Idempotency dependency for FastAPI endpoints
Handles request deduplication and ACID registration automatically
"""

from fastapi import Header, HTTPException, status, Depends
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_sys_db
from app.services.idempotency_service import IdempotencyService
from app.services.request_service import RequestService
from app.services.auth_service import get_current_user
from app.models import UserAccount, RequestStatus

async def get_idempotency_key(
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
) -> Optional[str]:
    """
    Dependency para obtener el header X-Idempotency-Key
    Si no se proporciona, retorna None (no se aplica idempotencia)
    """
    return x_idempotency_key

async def check_idempotency_and_register(
    x_idempotency_key: Optional[str] = Depends(get_idempotency_key),
    current_user: Optional[UserAccount] = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Dependency que verifica idempotencia y registra la solicitud
    Retorna un dict con:
    - is_duplicate: bool - Si es una solicitud duplicada
    - cached_response: Optional[Dict] - Respuesta cacheada si es duplicada
    - request_id: Optional[int] - ID del request registrado
    - x_idempotency_key: Optional[str] - La clave de idempotencia
    - idempotency_service: IdempotencyService
    - request_service: RequestService
    """
    idempotency_service = IdempotencyService(db)
    request_service = RequestService(db)
    
    result = {
        "is_duplicate": False,
        "cached_response": None,
        "request_id": None,
        "x_idempotency_key": x_idempotency_key,
        "idempotency_service": idempotency_service,
        "request_service": request_service
    }
    
    # Si no hay idempotency key, no se aplica idempotencia
    if not x_idempotency_key:
        return result
    
    # Verificar si existe una respuesta previa
    cached = await idempotency_service.check_idempotency_key(x_idempotency_key)
    
    if cached and cached.get("exists"):
        # Es una solicitud duplicada
        result["is_duplicate"] = True
        result["cached_response"] = cached.get("response")
        
        # Obtener el request asociado si existe
        request = await request_service.get_request_by_key(x_idempotency_key)
        if request:
            result["request_id"] = request.id
        
        return result
    
    # No es duplicada, crear registro ACID
    try:
        # Crear request
        request = await request_service.create_request(
            request_key=x_idempotency_key,
            user_id=current_user.id if current_user else None
        )
        result["request_id"] = request.id
        
        # Crear idempotency key
        await idempotency_service.create_idempotency_key(
            request_key=x_idempotency_key,
            request_id=request.id
        )
        
    except Exception as e:
        # Si hay error al crear, continuar sin idempotencia
        print(f"⚠️  Error al registrar idempotencia: {e}")
        pass
    
    return result

