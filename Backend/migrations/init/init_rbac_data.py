"""
Script de inicialización de datos RBAC (roles y permisos básicos)
Ejecutar una vez después de crear las tablas
"""

import sys
import os
from sqlalchemy.orm import Session
from app.core.database import SysSessionLocal
from app.models import Role, Permission, RolePermission

# Roles básicos
ROLES = [
    {
        "code": "admin",
        "name": "Administrator",
        "description": "Administrador del sistema con acceso completo"
    },
    {
        "code": "user",
        "name": "Regular User",
        "description": "Usuario regular con acceso básico"
    },
    {
        "code": "operator",
        "name": "Operator",
        "description": "Operador del sistema con acceso a proveedores"
    }
]

# Permisos básicos
PERMISSIONS = [
    # Predictions
    {"code": "predictions:read", "name": "Read Predictions", "scope": "predictions", "description": "Consultar predicciones"},
    {"code": "predictions:write", "name": "Create Predictions", "scope": "predictions", "description": "Crear predicciones"},
    
    # Bets
    {"code": "bets:read", "name": "Read Bets", "scope": "bets", "description": "Consultar apuestas"},
    {"code": "bets:write", "name": "Create Bets", "scope": "bets", "description": "Crear apuestas"},
    {"code": "bets:update", "name": "Update Bets", "scope": "bets", "description": "Actualizar apuestas"},
    
    # Users
    {"code": "users:read", "name": "Read Users", "scope": "users", "description": "Consultar usuarios"},
    {"code": "users:write", "name": "Create Users", "scope": "users", "description": "Crear usuarios"},
    {"code": "users:update", "name": "Update Users", "scope": "users", "description": "Actualizar usuarios"},
    
    # Admin
    {"code": "admin:read", "name": "Admin Read", "scope": "admin", "description": "Acceso de lectura administrativo"},
    {"code": "admin:write", "name": "Admin Write", "scope": "admin", "description": "Acceso de escritura administrativo"},
    
    # Providers
    {"code": "providers:read", "name": "Read Providers", "scope": "providers", "description": "Consultar proveedores"},
    {"code": "providers:write", "name": "Manage Providers", "scope": "providers", "description": "Gestionar proveedores"},
    
    # Audit
    {"code": "audit:read", "name": "Read Audit Log", "scope": "audit", "description": "Consultar logs de auditoría"},
]

# Asignación de permisos a roles
ROLE_PERMISSIONS = {
    "admin": [
        "predictions:read", "predictions:write",
        "bets:read", "bets:write", "bets:update",
        "users:read", "users:write", "users:update",
        "admin:read", "admin:write",
        "providers:read", "providers:write",
        "audit:read",
    ],
    "user": [
        "predictions:read",
        "bets:read", "bets:write",
        "users:read",  # Solo puede leer su propio perfil
    ],
    "operator": [
        "predictions:read",
        "bets:read",
        "providers:read", "providers:write",
        "audit:read",
    ]
}

def init_roles_and_permissions(db: Session):
    """Inicializar roles y permisos básicos"""
    print("🔧 Inicializando roles y permisos...")
    
    # Crear roles
    roles_dict = {}
    for role_data in ROLES:
        role = db.query(Role).filter(Role.code == role_data["code"]).first()
        if not role:
            role = Role(**role_data)
            db.add(role)
            print(f"  ✅ Creado rol: {role_data['code']}")
        else:
            print(f"  ⚠️  Rol ya existe: {role_data['code']}")
        roles_dict[role_data["code"]] = role
    
    # Crear permisos
    permissions_dict = {}
    for perm_data in PERMISSIONS:
        perm = db.query(Permission).filter(Permission.code == perm_data["code"]).first()
        if not perm:
            perm = Permission(**perm_data)
            db.add(perm)
            print(f"  ✅ Creado permiso: {perm_data['code']}")
        else:
            print(f"  ⚠️  Permiso ya existe: {perm_data['code']}")
        permissions_dict[perm_data["code"]] = perm
    
    db.commit()
    
    # Asignar permisos a roles
    print("\n🔗 Asignando permisos a roles...")
    for role_code, perm_codes in ROLE_PERMISSIONS.items():
        role = roles_dict[role_code]
        for perm_code in perm_codes:
            perm = permissions_dict[perm_code]
            # Verificar si ya existe la relación
            existing = db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == perm.id
            ).first()
            if not existing:
                role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
                db.add(role_perm)
                print(f"  ✅ Asignado permiso '{perm_code}' a rol '{role_code}'")
            else:
                print(f"  ⚠️  Permiso '{perm_code}' ya asignado a rol '{role_code}'")
    
    db.commit()
    print("\n✅ Inicialización de roles y permisos completada")

def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 INICIALIZACIÓN DE DATOS RBAC")
    print("=" * 60)
    
    db = SysSessionLocal()
    try:
        # Establecer search_path
        from sqlalchemy import text
        from app.core.config import settings
        db.execute(text(f"SET search_path TO {settings.DB_SCHEMA}, public"))
        db.commit()
        
        init_roles_and_permissions(db)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("✅ Proceso completado")
    print("=" * 60)

if __name__ == "__main__":
    main()

