"""
User Type Service - Maneja movimiento de usuarios entre tablas según roles
"""

from sqlalchemy.orm import Session
from typing import Optional, Literal
from app.models.user_accounts import UserAccount, Client, Administrator, Operator
from app.models.role import Role
from app.models.user_role import UserRole
from decimal import Decimal

UserTableType = Literal['client', 'administrator', 'operator']

class UserTypeService:
    """Service para manejar movimiento de usuarios entre tablas según roles"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_current_table(self, user_id: int) -> Optional[UserTableType]:
        """Determina en qué tabla está actualmente el usuario"""
        # Verificar en orden: administrator, operator, client
        admin = self.db.query(Administrator).filter(Administrator.user_account_id == user_id).first()
        if admin:
            return 'administrator'
        
        operator = self.db.query(Operator).filter(Operator.user_account_id == user_id).first()
        if operator:
            return 'operator'
        
        client = self.db.query(Client).filter(Client.user_account_id == user_id).first()
        if client:
            return 'client'
        
        return None
    
    def get_user_primary_role(self, user_id: int) -> Optional[Role]:
        """
        Obtiene el rol principal activo del usuario.
        Prioridad: admin > operator > client
        Si tiene múltiples roles activos, retorna el de mayor prioridad.
        """
        # Obtener todos los roles activos
        user_roles = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.is_active == True
        ).all()
        
        if not user_roles:
            # Si no tiene roles activos, retornar rol 'client' por defecto
            client_role = self.db.query(Role).filter(Role.code == 'client').first()
            return client_role
        
        # Obtener los roles
        roles = []
        for ur in user_roles:
            role = self.db.query(Role).filter(Role.id == ur.role_id).first()
            if role:
                roles.append(role)
        
        if not roles:
            # Si no se encontraron roles, retornar 'client' por defecto
            client_role = self.db.query(Role).filter(Role.code == 'client').first()
            return client_role
        
        # Prioridad: admin > operator > client
        for priority_code in ['admin', 'operator', 'client']:
            for role in roles:
                if role.code == priority_code:
                    return role
        
        # Si no coincide con prioridad, retornar el primero
        return roles[0]
    
    def move_user_to_table(self, user_id: int, target_role_code: str) -> bool:
        """
        Mueve un usuario a la tabla correspondiente según el rol.
        Preserva datos personales (first_name, last_name, phone, avatar_url, credits si aplica).
        
        Args:
            user_id: ID del usuario
            target_role_code: Código del rol objetivo ('client', 'admin', 'operator')
        
        Returns:
            True si se movió exitosamente, False si hubo error
        """
        # Obtener usuario
        user = self.db.query(UserAccount).filter(UserAccount.id == user_id).first()
        if not user:
            return False
        
        # Obtener rol objetivo
        target_role = self.db.query(Role).filter(Role.code == target_role_code).first()
        if not target_role:
            return False
        
        # Usar el código del rol de la BD directamente
        # Validar que sea uno de los códigos válidos
        # NO hacer fallback silencioso - esto causaría inconsistencias entre el rol asignado y la tabla
        valid_role_codes = ['client', 'admin', 'operator']
        role_code = target_role.code
        
        if role_code not in valid_role_codes:
            # Si el código del rol no es válido, fallar explícitamente
            # Esto previene inconsistencias donde el usuario tiene un rol asignado pero está en la tabla incorrecta
            # El endpoint debe manejar este error y no asignar roles con códigos no reconocidos
            return False
        
        # Obtener tabla actual
        current_table = self.get_user_current_table(user_id)
        
        # Si ya está en la tabla correcta, solo actualizar role_id
        # IMPORTANTE: Verificar que el registro existe antes de actualizar
        # Si current_table indica que está en la tabla correcta pero el registro es None
        # (posible condición de carrera), crear el registro directamente sin pasar por
        # la lógica de eliminación/recreación para evitar pérdida de datos y operaciones innecesarias
        if role_code == 'client' and current_table == 'client':
            client = self.db.query(Client).filter(Client.user_account_id == user_id).first()
            if client:
                client.role_id = target_role.id
                self.db.flush()
                return True
            # Si current_table == 'client' pero client es None, es una condición de carrera
            # Crear el registro directamente con valores por defecto
            # Obtener user_account para preserved_data básico
            user = self.db.query(UserAccount).filter(UserAccount.id == user_id).first()
            if not user:
                return False
            
            # Usar 0.0 para créditos en caso de race condition para mantener consistencia
            # con el flujo normal donde usuarios que vienen de administrator/operator
            # no reciben créditos no ganados. Si el usuario tenía créditos previos,
            # deberían estar preservados en preserved_data del flujo normal.
            client = Client(
                user_account_id=user_id,
                role_id=target_role.id,
                credits=Decimal('0.0'),  # Consistente con flujo normal - no créditos no ganados
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            self.db.add(client)
            self.db.flush()
            return True
        
        if role_code == 'admin' and current_table == 'administrator':
            admin = self.db.query(Administrator).filter(Administrator.user_account_id == user_id).first()
            if admin:
                admin.role_id = target_role.id
                self.db.flush()
                return True
            # Si current_table == 'administrator' pero admin es None, es una condición de carrera
            # Crear el registro directamente con valores por defecto
            user = self.db.query(UserAccount).filter(UserAccount.id == user_id).first()
            if not user:
                return False
            
            admin = Administrator(
                user_account_id=user_id,
                role_id=target_role.id,
                first_name='Admin',
                last_name='User',
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            self.db.add(admin)
            self.db.flush()
            return True
        
        if role_code == 'operator' and current_table == 'operator':
            operator = self.db.query(Operator).filter(Operator.user_account_id == user_id).first()
            if operator:
                operator.role_id = target_role.id
                self.db.flush()
                return True
            # Si current_table == 'operator' pero operator es None, es una condición de carrera
            # Crear el registro directamente con valores por defecto
            user = self.db.query(UserAccount).filter(UserAccount.id == user_id).first()
            if not user:
                return False
            
            operator = Operator(
                user_account_id=user_id,
                role_id=target_role.id,
                first_name='Operator',
                last_name='User',
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            self.db.add(operator)
            self.db.flush()
            return True
        
        # Preservar datos del registro actual
        preserved_data = {}
        if current_table == 'client':
            client = self.db.query(Client).filter(Client.user_account_id == user_id).first()
            if client:
                preserved_data = {
                    'first_name': client.first_name,
                    'last_name': client.last_name,
                    'phone': client.phone,
                    'avatar_url': client.avatar_url,
                    'credits': client.credits,
                    'date_of_birth': client.date_of_birth,
                    'created_at': client.created_at,
                    'updated_at': client.updated_at
                }
        elif current_table == 'administrator':
            admin = self.db.query(Administrator).filter(Administrator.user_account_id == user_id).first()
            if admin:
                preserved_data = {
                    'first_name': admin.first_name,
                    'last_name': admin.last_name,
                    'phone': admin.phone,
                    'avatar_url': admin.avatar_url,
                    'employee_id': admin.employee_id,
                    'department': admin.department,
                    'created_at': admin.created_at,
                    'updated_at': admin.updated_at
                }
        elif current_table == 'operator':
            operator = self.db.query(Operator).filter(Operator.user_account_id == user_id).first()
            if operator:
                preserved_data = {
                    'first_name': operator.first_name,
                    'last_name': operator.last_name,
                    'phone': operator.phone,
                    'avatar_url': operator.avatar_url,
                    'employee_id': operator.employee_id,
                    'department': operator.department,
                    'shift': operator.shift,
                    'created_at': operator.created_at,
                    'updated_at': operator.updated_at
                }
        else:
            # Si no está en ninguna tabla, usar datos por defecto
            # avatar_url ya no existe en user_accounts, así que será None
            preserved_data = {
                'first_name': None,
                'last_name': None,
                'phone': None,
                'avatar_url': None,  # avatar_url movido a tablas individuales
                'created_at': user.created_at,
                'updated_at': user.updated_at
            }
        
        # Eliminar registro de tabla actual
        if current_table == 'client':
            client = self.db.query(Client).filter(Client.user_account_id == user_id).first()
            if client:
                self.db.delete(client)
        elif current_table == 'administrator':
            admin = self.db.query(Administrator).filter(Administrator.user_account_id == user_id).first()
            if admin:
                self.db.delete(admin)
        elif current_table == 'operator':
            operator = self.db.query(Operator).filter(Operator.user_account_id == user_id).first()
            if operator:
                self.db.delete(operator)
        
        # Crear registro en tabla objetivo
        # Usar role_code para asegurar que siempre se cree un registro
        if role_code == 'client':
            # Preservar créditos solo si el usuario viene de la tabla client
            # Si viene de administrator o operator (que no tienen credits), usar 0.0
            # Esto previene que usuarios reciban créditos no ganados al cambiar de rol
            if 'credits' in preserved_data:
                # Usuario viene de client, preservar sus créditos actuales
                credits = preserved_data.get('credits')
                if credits is None:
                    credits = Decimal('0.0')
                else:
                    credits = Decimal(str(credits)) if not isinstance(credits, Decimal) else credits
            else:
                # Usuario viene de administrator o operator (no tienen credits)
                # Usar 0.0 en lugar de 1000.0 para evitar créditos no ganados
                credits = Decimal('0.0')
            
            client = Client(
                user_account_id=user_id,
                role_id=target_role.id,
                credits=credits,
                first_name=preserved_data.get('first_name'),
                last_name=preserved_data.get('last_name'),
                phone=preserved_data.get('phone'),
                date_of_birth=preserved_data.get('date_of_birth'),
                avatar_url=preserved_data.get('avatar_url'),
                created_at=preserved_data.get('created_at'),
                updated_at=preserved_data.get('updated_at')
            )
            self.db.add(client)
        
        elif role_code == 'admin':
            # Administrators requiere first_name y last_name
            first_name = preserved_data.get('first_name') or 'Admin'
            last_name = preserved_data.get('last_name') or 'User'
            
            admin = Administrator(
                user_account_id=user_id,
                role_id=target_role.id,
                first_name=first_name,
                last_name=last_name,
                phone=preserved_data.get('phone'),
                employee_id=preserved_data.get('employee_id'),
                department=preserved_data.get('department'),
                avatar_url=preserved_data.get('avatar_url'),
                created_at=preserved_data.get('created_at'),
                updated_at=preserved_data.get('updated_at')
            )
            self.db.add(admin)
        
        elif role_code == 'operator':
            # Operators requiere first_name y last_name
            first_name = preserved_data.get('first_name') or 'Operator'
            last_name = preserved_data.get('last_name') or 'User'
            
            operator = Operator(
                user_account_id=user_id,
                role_id=target_role.id,
                first_name=first_name,
                last_name=last_name,
                phone=preserved_data.get('phone'),
                employee_id=preserved_data.get('employee_id'),
                department=preserved_data.get('department'),
                shift=preserved_data.get('shift'),
                avatar_url=preserved_data.get('avatar_url'),
                created_at=preserved_data.get('created_at'),
                updated_at=preserved_data.get('updated_at')
            )
            self.db.add(operator)
        else:
            # Este bloque no debería ejecutarse si role_code pasó la validación inicial
            # Si llegamos aquí, es un error de programación - el código de rol no es válido
            # NO hacer fallback silencioso - fallar explícitamente
            return False
        
        self.db.flush()
        return True
    
    def ensure_user_in_correct_table(self, user_id: int) -> bool:
        """
        Asegura que el usuario esté en la tabla correcta según su rol activo.
        Si el usuario no tiene roles activos, lo mueve a 'client' por defecto.
        """
        primary_role = self.get_user_primary_role(user_id)
        if not primary_role:
            return False
        
        current_table = self.get_user_current_table(user_id)
        
        # Validar que el código del rol es uno de los códigos reconocidos
        # NO hacer fallback silencioso - esto causaría inconsistencias
        valid_role_codes = ['client', 'admin', 'operator']
        if primary_role.code not in valid_role_codes:
            # Si el código del rol no es válido, fallar explícitamente
            # Esto previene inconsistencias donde el usuario tiene un rol asignado pero está en la tabla incorrecta
            return False
        
        # Determinar tabla objetivo según rol
        target_table = None
        if primary_role.code == 'admin':
            target_table = 'administrator'
        elif primary_role.code == 'operator':
            target_table = 'operator'
        elif primary_role.code == 'client':
            target_table = 'client'
        else:
            # Esto no debería ocurrir porque ya validamos arriba, pero por seguridad
            return False
        
        # Si ya está en la tabla correcta, no hacer nada
        if (target_table == 'client' and current_table == 'client') or \
           (target_table == 'administrator' and current_table == 'administrator') or \
           (target_table == 'operator' and current_table == 'operator'):
            return True
        
        # Mover a la tabla correcta
        return self.move_user_to_table(user_id, primary_role.code)
