"""
Script para sincronizar el campo legacy 'rol' en users con los roles RBAC de user_roles
"""

import sys
from sqlalchemy.orm import Session
from app.core.database import SysSessionLocal
from app.models import User
from app.services.role_service import RoleService

def sync_all_users():
    """Sincroniza el campo legacy 'rol' para todos los usuarios"""
    db: Session = SysSessionLocal()
    role_service = RoleService(db)
    
    try:
        # Obtener todos los usuarios
        users = db.query(User).all()
        
        print("=" * 70)
        print("🔄 SINCRONIZACIÓN DE ROLES LEGACY")
        print("=" * 70)
        print(f"\n📋 Encontrados {len(users)} usuarios\n")
        
        updated_count = 0
        for user in users:
            old_rol = user.rol
            
            # Sincronizar rol
            role_service.sync_legacy_rol(user.id)
            
            # Refrescar usuario para ver el nuevo valor
            db.refresh(user)
            new_rol = user.rol
            
            if old_rol != new_rol:
                print(f"✅ {user.username}: '{old_rol}' → '{new_rol}'")
                updated_count += 1
            else:
                print(f"   {user.username}: '{old_rol}' (sin cambios)")
        
        print("\n" + "=" * 70)
        print(f"✅ Sincronización completada: {updated_count} usuarios actualizados")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def sync_user(username: str):
    """Sincroniza el campo legacy 'rol' para un usuario específico"""
    db: Session = SysSessionLocal()
    role_service = RoleService(db)
    
    try:
        # Buscar usuario
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ Error: Usuario '{username}' no encontrado")
            return False
        
        old_rol = user.rol
        
        # Sincronizar rol
        role_service.sync_legacy_rol(user.id)
        
        # Refrescar usuario para ver el nuevo valor
        db.refresh(user)
        new_rol = user.rol
        
        print("=" * 70)
        print(f"🔄 SINCRONIZACIÓN DE ROL LEGACY: {username}")
        print("=" * 70)
        print(f"   Rol anterior: '{old_rol}'")
        print(f"   Rol nuevo: '{new_rol}'")
        
        if old_rol != new_rol:
            print(f"✅ Rol actualizado correctamente")
        else:
            print(f"   ℹ️  El rol ya estaba sincronizado")
        
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Función principal"""
    if len(sys.argv) > 1:
        username = sys.argv[1]
        sync_user(username)
    else:
        sync_all_users()

if __name__ == "__main__":
    main()

