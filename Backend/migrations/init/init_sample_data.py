"""
Script para insertar datos iniciales de ejemplo en las bases de datos
"""

import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SysSessionLocal, EspnSessionLocal
from app.models import (
    User, Role, Permission, UserRole, RolePermission,
    Request, RequestStatus, IdempotencyKey, Prediction, ModelVersion,
    AuditLog, Outbox
)
from app.services.auth_service import get_password_hash
import uuid
import json

def init_sample_users(db: Session):
    """Crear usuarios de ejemplo"""
    print("👤 Creando usuarios de ejemplo...")
    
    # Verificar si ya existen usuarios
    existing_users = db.query(User).count()
    if existing_users > 0:
        print(f"  ⚠️  Ya existen {existing_users} usuarios, omitiendo creación")
        return
    
    # Crear usuarios de ejemplo
    users_data = [
        {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "test123",
            "rol": "usuario",
            "credits": 1500.0
        },
        {
            "username": "testoperator",
            "email": "operator@example.com",
            "password": "test123",
            "rol": "operator",
            "credits": 2000.0
        }
    ]
    
    for user_data in users_data:
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            rol=user_data["rol"],
            credits=user_data["credits"],
            is_active=True
        )
        db.add(user)
    
    db.commit()
    print(f"  ✅ Creados {len(users_data)} usuarios de ejemplo")

def init_sample_requests(db: Session):
    """Crear requests de ejemplo"""
    print("📋 Creando requests de ejemplo...")
    
    # Obtener usuarios
    users = db.query(User).all()
    if not users:
        print("  ⚠️  No hay usuarios, omitiendo creación de requests")
        return
    
    # Verificar si ya existen requests
    existing_requests = db.query(Request).count()
    if existing_requests > 0:
        print(f"  ⚠️  Ya existen {existing_requests} requests, omitiendo creación")
        return
    
    statuses = [RequestStatus.COMPLETED, RequestStatus.COMPLETED, RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.PROCESSING]
    
    for i in range(20):
        user = users[i % len(users)]
        request_key = str(uuid.uuid4())
        status = statuses[i % len(statuses)]
        
        request = Request(
            request_key=request_key,
            event_id=401585600 + i if i % 2 == 0 else None,
            user_id=user.id,
            status=status,
            request_metadata=json.dumps({"source": "test", "index": i}),
            error_message=f"Error de prueba {i}" if status == RequestStatus.FAILED else None,
            created_at=datetime.utcnow() - timedelta(hours=i),
            completed_at=datetime.utcnow() - timedelta(hours=i-1) if status == RequestStatus.COMPLETED else None
        )
        db.add(request)
    
    db.commit()
    print("  ✅ Creados 20 requests de ejemplo")

def init_sample_predictions(db: Session):
    """Crear predicciones de ejemplo"""
    print("🔮 Creando predicciones de ejemplo...")
    
    # Obtener requests completados
    requests = db.query(Request).filter(Request.status == RequestStatus.COMPLETED).limit(10).all()
    if not requests:
        print("  ⚠️  No hay requests completados, omitiendo creación de predicciones")
        return
    
    # Obtener versión del modelo
    model_version = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
    if not model_version:
        print("  ⚠️  No hay versión de modelo activa, omitiendo creación de predicciones")
        return
    
    # Verificar si ya existen predicciones
    existing_predictions = db.query(Prediction).count()
    if existing_predictions > 0:
        print(f"  ⚠️  Ya existen {existing_predictions} predicciones, omitiendo creación")
        return
    
    import random
    
    for request in requests:
        prediction = Prediction(
            request_id=request.id,
            model_version_id=model_version.id,
            telemetry=json.dumps({
                "home_win_probability": round(random.uniform(0.3, 0.7), 3),
                "away_win_probability": round(random.uniform(0.3, 0.7), 3),
                "predicted_home_score": round(random.uniform(90, 120), 1),
                "predicted_away_score": round(random.uniform(90, 120), 1),
            }),
            latency_ms=round(random.uniform(50, 500), 2),
            score=json.dumps({
                "confidence": round(random.uniform(0.6, 0.95), 3),
                "accuracy": round(random.uniform(0.7, 0.98), 3)
            }),
            created_at=request.created_at
        )
        db.add(prediction)
    
    db.commit()
    print(f"  ✅ Creadas {len(requests)} predicciones de ejemplo")

def init_sample_audit_logs(db: Session):
    """Crear logs de auditoría de ejemplo"""
    print("📝 Creando logs de auditoría de ejemplo...")
    
    # Verificar si ya existen logs
    existing_logs = db.query(AuditLog).count()
    if existing_logs > 0:
        print(f"  ⚠️  Ya existen {existing_logs} logs de auditoría, omitiendo creación")
        return
    
    users = db.query(User).all()
    if not users:
        print("  ⚠️  No hay usuarios, omitiendo creación de logs")
        return
    
    actions = ["create", "update", "delete", "read"]
    resource_types = ["user", "role", "bet", "prediction", "request"]
    
    for i in range(30):
        user = users[i % len(users)]
        action = actions[i % len(actions)]
        resource_type = resource_types[i % len(resource_types)]
        
        log = AuditLog(
            actor_user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=i + 1,
            before=json.dumps({"old_value": f"before_{i}"}) if action in ["update", "delete"] else None,
            after=json.dumps({"new_value": f"after_{i}"}) if action in ["create", "update"] else None,
            audit_metadata=json.dumps({"ip": "127.0.0.1", "user_agent": "test"}),
            created_at=datetime.utcnow() - timedelta(hours=i)
        )
        db.add(log)
    
    db.commit()
    print("  ✅ Creados 30 logs de auditoría de ejemplo")

def init_sample_outbox(db: Session):
    """Crear eventos de outbox de ejemplo"""
    print("📦 Creando eventos de outbox de ejemplo...")
    
    # Verificar si ya existen eventos
    existing_events = db.query(Outbox).count()
    if existing_events > 0:
        print(f"  ⚠️  Ya existen {existing_events} eventos de outbox, omitiendo creación")
        return
    
    requests = db.query(Request).limit(15).all()
    if not requests:
        print("  ⚠️  No hay requests, omitiendo creación de eventos")
        return
    
    event_types = ["prediction.completed", "prediction.failed", "bet.placed", "user.created"]
    
    for i, request in enumerate(requests):
        event_type = event_types[i % len(event_types)]
        published = i % 3 != 0  # Algunos publicados, otros no
        
        event = Outbox(
            topic=event_type,
            payload=json.dumps({
                "request_id": request.id,
                "request_key": request.request_key,
                "status": request.status.value if hasattr(request.status, 'value') else str(request.status),
                "timestamp": datetime.utcnow().isoformat()
            }),
            published_at=datetime.utcnow() - timedelta(hours=i) if published else None,
            created_at=datetime.utcnow() - timedelta(hours=i)
        )
        db.add(event)
    
    db.commit()
    print(f"  ✅ Creados {len(requests)} eventos de outbox de ejemplo")

def init_sample_idempotency_keys(db: Session):
    """Crear idempotency keys de ejemplo"""
    print("🔑 Creando idempotency keys de ejemplo...")
    
    # Verificar si ya existen keys
    existing_keys = db.query(IdempotencyKey).count()
    if existing_keys > 0:
        print(f"  ⚠️  Ya existen {existing_keys} idempotency keys, omitiendo creación")
        return
    
    requests = db.query(Request).limit(10).all()
    if not requests:
        print("  ⚠️  No hay requests, omitiendo creación de keys")
        return
    
    for request in requests:
        key = IdempotencyKey(
            request_key=request.request_key,
            request_id=request.id,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            created_at=request.created_at
        )
        db.add(key)
    
    db.commit()
    print(f"  ✅ Creadas {len(requests)} idempotency keys de ejemplo")

def main():
    """Función principal"""
    print("=" * 70)
    print("🚀 INICIALIZACIÓN DE DATOS DE EJEMPLO")
    print("=" * 70)
    
    db: Session = SysSessionLocal()
    
    try:
        # Inicializar datos
        init_sample_users(db)
        init_sample_requests(db)
        init_sample_predictions(db)
        init_sample_audit_logs(db)
        init_sample_outbox(db)
        init_sample_idempotency_keys(db)
        
        print("\n" + "=" * 70)
        print("✅ Inicialización completada exitosamente")
        print("=" * 70)
        
        # Mostrar resumen
        print("\n📊 RESUMEN:")
        print(f"  Usuarios: {db.query(User).count()}")
        print(f"  Requests: {db.query(Request).count()}")
        print(f"  Predictions: {db.query(Prediction).count()}")
        print(f"  Audit Logs: {db.query(AuditLog).count()}")
        print(f"  Outbox Events: {db.query(Outbox).count()}")
        print(f"  Idempotency Keys: {db.query(IdempotencyKey).count()}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

