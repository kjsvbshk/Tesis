-- ============================================================================
-- MIGRACIÓN: Separación de usuarios por tipo (Cliente, Administrador, Operador)
-- ============================================================================
-- Este script separa la tabla users en tres tablas específicas según el tipo
-- de usuario, cada una relacionada con su respectivo rol.
--
-- Fecha: 2025-01-XX
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. CREAR TABLA BASE DE USUARIOS (CAMPOS COMUNES)
-- ============================================================================
-- Mantener una tabla base con campos comunes a todos los tipos de usuario
-- Esto permite autenticación unificada y evita duplicación

CREATE TABLE IF NOT EXISTS app.user_accounts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Crear índice adicional para is_active (los UNIQUE ya crean índices automáticamente)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'user_accounts' AND indexname = 'idx_user_accounts_active') THEN
        CREATE INDEX idx_user_accounts_active ON app.user_accounts(is_active);
    END IF;
END $$;

-- ============================================================================
-- 2. CREAR TABLA DE CLIENTES (REEMPLAZA "usuario")
-- ============================================================================
-- Los clientes son usuarios que pueden apostar

CREATE TABLE IF NOT EXISTS app.clients (
    id SERIAL PRIMARY KEY,
    user_account_id INTEGER NOT NULL UNIQUE,
    role_id INTEGER NOT NULL, -- FK a roles (rol "cliente" o "user")
    credits NUMERIC(10, 2) DEFAULT 1000.0 NOT NULL CHECK (credits >= 0),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    date_of_birth DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_clients_user_account FOREIGN KEY (user_account_id) 
        REFERENCES app.user_accounts(id) ON DELETE CASCADE,
    CONSTRAINT fk_clients_role FOREIGN KEY (role_id) 
        REFERENCES app.roles(id) ON DELETE RESTRICT
);

-- Crear índices condicionalmente
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'clients' AND indexname = 'idx_clients_user_account_id') THEN
        CREATE INDEX idx_clients_user_account_id ON app.clients(user_account_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'clients' AND indexname = 'idx_clients_role_id') THEN
        CREATE INDEX idx_clients_role_id ON app.clients(role_id);
    END IF;
END $$;

-- ============================================================================
-- 3. CREAR TABLA DE ADMINISTRADORES
-- ============================================================================
-- Los administradores gestionan el sistema

CREATE TABLE IF NOT EXISTS app.administrators (
    id SERIAL PRIMARY KEY,
    user_account_id INTEGER NOT NULL UNIQUE,
    role_id INTEGER NOT NULL, -- FK a roles (rol "admin")
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    employee_id VARCHAR(50) UNIQUE,
    department VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_administrators_user_account FOREIGN KEY (user_account_id) 
        REFERENCES app.user_accounts(id) ON DELETE CASCADE,
    CONSTRAINT fk_administrators_role FOREIGN KEY (role_id) 
        REFERENCES app.roles(id) ON DELETE RESTRICT
);

-- Crear índices condicionalmente
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'administrators' AND indexname = 'idx_administrators_user_account_id') THEN
        CREATE INDEX idx_administrators_user_account_id ON app.administrators(user_account_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'administrators' AND indexname = 'idx_administrators_role_id') THEN
        CREATE INDEX idx_administrators_role_id ON app.administrators(role_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'administrators' AND indexname = 'idx_administrators_employee_id') THEN
        CREATE INDEX idx_administrators_employee_id ON app.administrators(employee_id);
    END IF;
END $$;

-- ============================================================================
-- 4. CREAR TABLA DE OPERADORES
-- ============================================================================
-- Los operadores gestionan operaciones del día a día

CREATE TABLE IF NOT EXISTS app.operators (
    id SERIAL PRIMARY KEY,
    user_account_id INTEGER NOT NULL UNIQUE,
    role_id INTEGER NOT NULL, -- FK a roles (rol "operator")
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    employee_id VARCHAR(50) UNIQUE,
    department VARCHAR(100),
    phone VARCHAR(20),
    shift VARCHAR(50), -- Turno de trabajo (ej: "mañana", "tarde", "noche")
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_operators_user_account FOREIGN KEY (user_account_id) 
        REFERENCES app.user_accounts(id) ON DELETE CASCADE,
    CONSTRAINT fk_operators_role FOREIGN KEY (role_id) 
        REFERENCES app.roles(id) ON DELETE RESTRICT
);

-- Crear índices condicionalmente
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'operators' AND indexname = 'idx_operators_user_account_id') THEN
        CREATE INDEX idx_operators_user_account_id ON app.operators(user_account_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'operators' AND indexname = 'idx_operators_role_id') THEN
        CREATE INDEX idx_operators_role_id ON app.operators(role_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'operators' AND indexname = 'idx_operators_employee_id') THEN
        CREATE INDEX idx_operators_employee_id ON app.operators(employee_id);
    END IF;
END $$;

-- ============================================================================
-- 5. CREAR ROLES SI NO EXISTEN
-- ============================================================================
-- Asegurar que existan los roles necesarios

INSERT INTO app.roles (code, name, description) VALUES
    ('client', 'Cliente', 'Usuario que puede realizar apuestas'),
    ('admin', 'Administrador', 'Administrador del sistema con acceso completo'),
    ('operator', 'Operador', 'Operador del sistema con permisos limitados')
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 6. MIGRAR DATOS DESDE app.users
-- ============================================================================
-- Migrar usuarios existentes a la nueva estructura

DO $$
DECLARE
    v_user_record RECORD;
    v_role_id INTEGER;
    v_client_id INTEGER;
    v_admin_id INTEGER;
    v_operator_id INTEGER;
BEGIN
    -- Obtener IDs de roles
    SELECT id INTO v_role_id FROM app.roles WHERE code = 'client' LIMIT 1;
    IF v_role_id IS NULL THEN
        INSERT INTO app.roles (code, name, description) VALUES ('client', 'Cliente', 'Usuario que puede realizar apuestas') RETURNING id INTO v_role_id;
    END IF;
    
    SELECT id INTO v_admin_id FROM app.roles WHERE code = 'admin' LIMIT 1;
    IF v_admin_id IS NULL THEN
        INSERT INTO app.roles (code, name, description) VALUES ('admin', 'Administrador', 'Administrador del sistema') RETURNING id INTO v_admin_id;
    END IF;
    
    SELECT id INTO v_operator_id FROM app.roles WHERE code = 'operator' LIMIT 1;
    IF v_operator_id IS NULL THEN
        INSERT INTO app.roles (code, name, description) VALUES ('operator', 'Operador', 'Operador del sistema') RETURNING id INTO v_operator_id;
    END IF;
    
    -- Verificar si existe la tabla app.users
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'app' AND table_name = 'users') THEN
        
        -- Migrar cada usuario según su rol
        FOR v_user_record IN 
            SELECT u.*, 
                   COALESCE(ur.role_id, 
                            CASE 
                                WHEN u.rol = 'admin' THEN v_admin_id
                                WHEN u.rol = 'operator' THEN v_operator_id
                                ELSE v_role_id
                            END) as assigned_role_id
            FROM app.users u
            LEFT JOIN app.user_roles ur ON u.id = ur.user_id AND ur.is_active = TRUE
            ORDER BY u.id
        LOOP
            -- Crear cuenta de usuario (mantener el mismo ID usando OVERRIDING SYSTEM VALUE)
            INSERT INTO app.user_accounts (id, username, email, hashed_password, is_active, created_at, updated_at)
            VALUES (
                v_user_record.id,
                v_user_record.username,
                v_user_record.email,
                v_user_record.hashed_password,
                v_user_record.is_active,
                v_user_record.created_at,
                v_user_record.updated_at
            )
            ON CONFLICT (username) DO UPDATE SET
                email = EXCLUDED.email,
                hashed_password = EXCLUDED.hashed_password,
                is_active = EXCLUDED.is_active,
                updated_at = EXCLUDED.updated_at;
            
            -- Determinar tipo de usuario y crear registro correspondiente
            IF v_user_record.rol = 'admin' OR v_user_record.assigned_role_id = v_admin_id THEN
                -- Es administrador
                INSERT INTO app.administrators (
                    user_account_id, role_id, 
                    first_name, last_name,
                    created_at, updated_at
                )
                VALUES (
                    v_user_record.id, v_admin_id,
                    'Admin', 
                    'User',
                    v_user_record.created_at, v_user_record.updated_at
                )
                ON CONFLICT (user_account_id) DO NOTHING;
                
            ELSIF v_user_record.rol = 'operator' OR v_user_record.assigned_role_id = v_operator_id THEN
                -- Es operador
                INSERT INTO app.operators (
                    user_account_id, role_id,
                    first_name, last_name,
                    created_at, updated_at
                )
                VALUES (
                    v_user_record.id, v_operator_id,
                    'Operator',
                    'User',
                    v_user_record.created_at, v_user_record.updated_at
                )
                ON CONFLICT (user_account_id) DO NOTHING;
                
            ELSE
                -- Es cliente (por defecto)
                INSERT INTO app.clients (user_account_id, role_id, credits, created_at, updated_at)
                VALUES (v_user_record.id, v_role_id, COALESCE(v_user_record.credits, 1000.0), v_user_record.created_at, v_user_record.updated_at)
                ON CONFLICT (user_account_id) DO NOTHING;
            END IF;
        END LOOP;
        
        -- Ajustar la secuencia para evitar conflictos de IDs futuros
        PERFORM setval('app.user_accounts_id_seq', GREATEST(
            (SELECT COALESCE(MAX(id), 0) FROM app.user_accounts),
            (SELECT COALESCE(MAX(id), 0) FROM app.users)
        ));
        
        RAISE NOTICE 'Datos migrados desde app.users a las nuevas tablas';
    ELSE
        RAISE NOTICE 'Tabla app.users no existe, omitiendo migración';
    END IF;
END $$;

-- ============================================================================
-- 7. ACTUALIZAR REFERENCIAS EN OTRAS TABLAS
-- ============================================================================
-- Actualizar foreign keys que referencian app.users para que apunten a app.user_accounts

-- Actualizar app.bets (si existe y está en app schema)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'app' AND table_name = 'bets') THEN
        -- Agregar constraint si no existe
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_schema = 'app' 
            AND table_name = 'bets' 
            AND constraint_name = 'fk_bets_user_account'
        ) THEN
            ALTER TABLE app.bets 
            ADD CONSTRAINT fk_bets_user_account 
            FOREIGN KEY (user_id) REFERENCES app.user_accounts(id) ON DELETE RESTRICT;
        END IF;
    END IF;
END $$;

-- Actualizar app.transactions (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'app' AND table_name = 'transactions') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_schema = 'app' 
            AND table_name = 'transactions' 
            AND constraint_name = 'fk_transactions_user_account'
        ) THEN
            ALTER TABLE app.transactions 
            ADD CONSTRAINT fk_transactions_user_account 
            FOREIGN KEY (user_id) REFERENCES app.user_accounts(id) ON DELETE RESTRICT;
        END IF;
    END IF;
END $$;

-- Actualizar app.audit_logs (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'app' AND table_name = 'audit_logs') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_schema = 'app' 
            AND table_name = 'audit_logs' 
            AND constraint_name = 'fk_audit_logs_user_account'
        ) THEN
            ALTER TABLE app.audit_logs 
            ADD CONSTRAINT fk_audit_logs_user_account 
            FOREIGN KEY (user_id) REFERENCES app.user_accounts(id) ON DELETE SET NULL;
        END IF;
    END IF;
END $$;

-- Actualizar espn.bets (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'espn' AND table_name = 'bets') THEN
        -- Nota: No podemos agregar FK porque está en otro esquema, pero documentamos la relación
        RAISE NOTICE 'Tabla espn.bets existe. user_id debe referenciar app.user_accounts.id manualmente.';
    END IF;
END $$;

-- ============================================================================
-- 8. CREAR VISTAS PARA FACILITAR CONSULTAS
-- ============================================================================

-- Vista unificada de todos los usuarios con su tipo
CREATE OR REPLACE VIEW app.users_unified AS
SELECT 
    ua.id,
    ua.username,
    ua.email,
    ua.is_active,
    ua.created_at,
    ua.updated_at,
    'client' as user_type,
    c.id as type_specific_id,
    c.role_id,
    r.code as role_code,
    r.name as role_name,
    c.credits,
    NULL::VARCHAR as employee_id,
    NULL::VARCHAR as department,
    NULL::VARCHAR as shift
FROM app.user_accounts ua
INNER JOIN app.clients c ON ua.id = c.user_account_id
INNER JOIN app.roles r ON c.role_id = r.id

UNION ALL

SELECT 
    ua.id,
    ua.username,
    ua.email,
    ua.is_active,
    ua.created_at,
    ua.updated_at,
    'administrator' as user_type,
    a.id as type_specific_id,
    a.role_id,
    r.code as role_code,
    r.name as role_name,
    NULL::NUMERIC as credits,
    a.employee_id,
    a.department,
    NULL::VARCHAR as shift
FROM app.user_accounts ua
INNER JOIN app.administrators a ON ua.id = a.user_account_id
INNER JOIN app.roles r ON a.role_id = r.id

UNION ALL

SELECT 
    ua.id,
    ua.username,
    ua.email,
    ua.is_active,
    ua.created_at,
    ua.updated_at,
    'operator' as user_type,
    o.id as type_specific_id,
    o.role_id,
    r.code as role_code,
    r.name as role_name,
    NULL::NUMERIC as credits,
    o.employee_id,
    o.department,
    o.shift
FROM app.user_accounts ua
INNER JOIN app.operators o ON ua.id = o.user_account_id
INNER JOIN app.roles r ON o.role_id = r.id;

-- ============================================================================
-- 9. COMENTARIOS Y DOCUMENTACIÓN
-- ============================================================================

COMMENT ON TABLE app.user_accounts IS 'Tabla base con información común de autenticación para todos los tipos de usuario';
COMMENT ON TABLE app.clients IS 'Clientes del sistema (reemplaza usuarios regulares). Pueden realizar apuestas.';
COMMENT ON TABLE app.administrators IS 'Administradores del sistema con acceso completo';
COMMENT ON TABLE app.operators IS 'Operadores del sistema con permisos limitados para operaciones del día a día';

COMMENT ON COLUMN app.clients.role_id IS 'Debe referenciar al rol "client" o "user"';
COMMENT ON COLUMN app.administrators.role_id IS 'Debe referenciar al rol "admin"';
COMMENT ON COLUMN app.operators.role_id IS 'Debe referenciar al rol "operator"';

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================

COMMIT;

-- ============================================================================
-- NOTAS POST-MIGRACIÓN:
-- ============================================================================
-- 1. La tabla app.users puede mantenerse para compatibilidad temporal o
--    eliminarse después de verificar que todo funciona correctamente
-- 2. Actualizar los modelos de SQLAlchemy para usar las nuevas tablas
-- 3. Actualizar servicios de autenticación para usar user_accounts
-- 4. Actualizar endpoints y servicios que usan User model
-- 5. La vista app.users_unified facilita consultas que necesitan todos los usuarios
-- ============================================================================

