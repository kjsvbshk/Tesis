"""
Request endpoints for RF-03
Query and manage ACID transaction registrations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_sys_db
from app.models import UserAccount, Request, RequestStatus
from app.services.auth_service import get_current_user
from app.services.request_service import RequestService
from app.core.authorization import get_user_permissions, has_permission

router = APIRouter()

@router.get("/me", response_model=List[dict])
async def get_my_requests(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Obtener mis requests (solicitudes del usuario actual)
    """
    try:
        request_service = RequestService(db)
        
        # Convertir status string a enum si se proporciona
        status_enum = None
        if status_filter:
            try:
                status_enum = RequestStatus(status_filter.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Status inválido: {status_filter}. Valores válidos: {[s.value for s in RequestStatus]}"
                )
        
        requests = await request_service.get_user_requests(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            status=status_enum
        )
        
        # Convertir a dict para respuesta
        return [
            {
                "id": r.id,
                "request_key": r.request_key,
                "status": r.status.value,
                "event_id": r.event_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_message": r.error_message
            }
            for r in requests
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching requests: {str(e)}")

@router.get("/{request_id}", response_model=dict)
async def get_request(
    request_id: int,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Obtener un request específico por ID
    Solo el usuario propietario o admin puede verlo
    """
    try:
        request_service = RequestService(db)
        request = await request_service.get_request_by_id(request_id)
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Verificar permisos: solo el propietario o admin
        user_permissions = get_user_permissions(db, current_user.id)
        is_admin = has_permission("admin:read", user_permissions)
        
        if request.user_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this request"
            )
        
        # Cargar metadata si existe
        request_metadata = None
        if request.request_metadata:
            import json
            try:
                request_metadata = json.loads(request.request_metadata)
            except:
                request_metadata = request.request_metadata
        
        return {
            "id": request.id,
            "request_key": request.request_key,
            "user_id": request.user_id,
            "event_id": request.event_id,
            "organization_id": request.organization_id,
            "market_id": request.market_id,
            "status": request.status.value,
            "request_metadata": request_metadata,
            "error_message": request.error_message,
            "created_at": request.created_at.isoformat() if request.created_at else None,
            "updated_at": request.updated_at.isoformat() if request.updated_at else None,
            "completed_at": request.completed_at.isoformat() if request.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching request: {str(e)}")

@router.get("/key/{request_key}", response_model=dict)
async def get_request_by_key(
    request_key: str,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Obtener un request por request_key
    Solo el usuario propietario o admin puede verlo
    """
    try:
        request_service = RequestService(db)
        request = await request_service.get_request_by_key(request_key)
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Verificar permisos: solo el propietario o admin
        try:
            user_permissions = get_user_permissions(db, current_user.id)
            is_admin = has_permission("admin:read", user_permissions)
        except Exception as perm_error:
            # Si hay error con permisos, solo verificar si es el propietario
            is_admin = False
        
        # Verificar si el usuario es el propietario o admin
        is_owner = request.user_id is not None and request.user_id == current_user.id
        
        if not is_owner and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this request"
            )
        
        # Cargar metadata si existe
        request_metadata = None
        if request.request_metadata:
            import json
            try:
                request_metadata = json.loads(request.request_metadata)
            except:
                request_metadata = request.request_metadata
        
        # Manejar status como enum o string
        status_value = request.status.value if hasattr(request.status, 'value') else str(request.status)
        
        return {
            "id": request.id,
            "request_key": request.request_key,
            "user_id": request.user_id,
            "event_id": request.event_id,
            "organization_id": request.organization_id,
            "market_id": request.market_id,
            "status": status_value,
            "request_metadata": request_metadata,
            "error_message": request.error_message,
            "created_at": request.created_at.isoformat() if request.created_at else None,
            "updated_at": request.updated_at.isoformat() if request.updated_at else None,
            "completed_at": request.completed_at.isoformat() if request.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching request: {str(e)}")

@router.get("/", response_model=List[dict])
async def search_requests(
    request_key: Optional[str] = Query(None),
    event_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    Buscar requests con múltiples filtros (admin only)
    """
    try:
        # Verificar permisos de admin
        user_permissions = get_user_permissions(db, current_user.id)
        if not has_permission("admin:read", user_permissions):
            raise HTTPException(
                status_code=403,
                detail="Admin permission required"
            )
        
        request_service = RequestService(db)
        
        # Convertir status string a enum si se proporciona
        status_enum = None
        if status_filter:
            try:
                status_enum = RequestStatus(status_filter.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Status inválido: {status_filter}"
                )
        
        # Convertir fechas si se proporcionan
        date_from_obj = None
        date_to_obj = None
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            except:
                raise HTTPException(status_code=400, detail="date_from formato inválido (usar ISO 8601)")
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except:
                raise HTTPException(status_code=400, detail="date_to formato inválido (usar ISO 8601)")
        
        requests = await request_service.search_requests(
            request_key=request_key,
            event_id=event_id,
            status=status_enum,
            date_from=date_from_obj,
            date_to=date_to_obj,
            limit=limit,
            offset=offset
        )
        
        # Convertir a dict para respuesta
        return [
            {
                "id": r.id,
                "request_key": r.request_key,
                "user_id": r.user_id,
                "event_id": r.event_id,
                "status": r.status.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_message": r.error_message
            }
            for r in requests
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching requests: {str(e)}")

