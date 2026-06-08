"""
Script de inicialización de datos básicos
- Modelo version activo
- Proveedores básicos
Ejecutar una vez después de crear las tablas
"""

import sys
import os
from sqlalchemy.orm import Session
from app.core.database import SysSessionLocal
from app.models import ModelVersion, Provider, ProviderEndpoint

def init_basic_data(db: Session):
    """Inicializa datos básicos en la base de datos"""
    print("Initializing basic data...")

    # Crear versión de modelo activa
    model_version = db.query(ModelVersion).filter(
        ModelVersion.version == "v1.0.0",
        ModelVersion.is_active == True
    ).first()
    
    if not model_version:
        # Desactivar cualquier versión activa previa
        db.query(ModelVersion).filter(ModelVersion.is_active == True).update({"is_active": False})
        
        # Crear nueva versión activa
        model_version = ModelVersion(
            version="v1.0.0",
            is_active=True,
            description="Versión inicial del modelo de predicción NBA",
            model_metadata='{"type": "placeholder", "accuracy": 0.0}'
        )
        db.add(model_version)
        db.commit()
        db.refresh(model_version)
        print(f"  ✅ Model version '{model_version.version}' created and activated.")
    else:
        print(f"  ℹ️  Model version '{model_version.version}' already exists and is active.")

    # Crear proveedores básicos
    providers_data = [
        {
            "code": "espn",
            "name": "ESPN API",
            "is_active": True,
            "timeout_seconds": 30,
            "max_retries": 3,
            "circuit_breaker_threshold": 5
        },
        {
            "code": "odds_api",
            "name": "Odds API",
            "is_active": True,
            "timeout_seconds": 30,
            "max_retries": 3,
            "circuit_breaker_threshold": 5
        }
    ]

    for provider_data in providers_data:
        provider = db.query(Provider).filter_by(code=provider_data["code"]).first()
        if not provider:
            provider = Provider(**provider_data)
            db.add(provider)
            db.commit()
            db.refresh(provider)
            print(f"  ✅ Provider '{provider.name}' created.")
        else:
            print(f"  ℹ️  Provider '{provider.name}' already exists.")

    # Crear endpoints de proveedores
    endpoints_data = [
        {
            "provider_code": "espn",
            "purpose": "get_odds",
            "url": "https://api.example.com/espn/odds",
            "method": "GET",
            "headers": '{"Content-Type": "application/json"}'
        },
        {
            "provider_code": "espn",
            "purpose": "get_stats",
            "url": "https://api.example.com/espn/stats",
            "method": "GET",
            "headers": '{"Content-Type": "application/json"}'
        },
        {
            "provider_code": "odds_api",
            "purpose": "get_odds",
            "url": "https://api.example.com/odds",
            "method": "GET",
            "headers": '{"Content-Type": "application/json"}'
        }
    ]

    for endpoint_data in endpoints_data:
        provider = db.query(Provider).filter_by(code=endpoint_data["provider_code"]).first()
        if not provider:
            print(f"  ⚠️  Provider '{endpoint_data['provider_code']}' not found, skipping endpoint.")
            continue
        
        endpoint = db.query(ProviderEndpoint).filter_by(
            provider_id=provider.id,
            purpose=endpoint_data["purpose"]
        ).first()
        
        if not endpoint:
            endpoint = ProviderEndpoint(
                provider_id=provider.id,
                purpose=endpoint_data["purpose"],
                url=endpoint_data["url"],
                method=endpoint_data["method"],
                headers=endpoint_data.get("headers")
            )
            db.add(endpoint)
            db.commit()
            print(f"  ✅ Endpoint '{endpoint_data['purpose']}' for provider '{endpoint_data['provider_code']}' created.")
        else:
            print(f"  ℹ️  Endpoint '{endpoint_data['purpose']}' for provider '{endpoint_data['provider_code']}' already exists.")
    
    print("Basic data initialization complete.")

def main():
    """Main function to run the basic data initialization"""
    print("=" * 60)
    print("🚀 INICIALIZACIÓN DE DATOS BÁSICOS")
    print("=" * 60)

    try:
        db: Session = SysSessionLocal()
        init_basic_data(db)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'db' in locals() and db:
            db.close()
    
    print("\n" + "=" * 60)
    print("✅ Proceso completado")
    print("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()

