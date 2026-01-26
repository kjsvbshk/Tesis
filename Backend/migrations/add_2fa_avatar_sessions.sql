-- ============================================================================
-- MIGRACIÓN: Agregar 2FA y Sesiones de Usuario
-- ============================================================================
-- Este script agrega las nuevas funcionalidades:
-- 1. Tabla user_two_factor para autenticación de dos factores
-- 2. Tabla user_sessions para rastrear sesiones activas
--
-- NOTA: avatar_url ahora está en las tablas individuales (clients, administrators, operators)
-- y no se agrega a user_accounts
--
-- Fecha: 2025-01-XX
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. CREAR TABLA user_two_factor
-- ============================================================================
-- Almacena la configuración de 2FA para cada usuario

CREATE TABLE IF NOT EXISTS app.user_two_factor (
    id SERIAL PRIMARY KEY,
    user_account_id INTEGER NOT NULL UNIQUE,
    secret VARCHAR(32) NOT NULL,
    is_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    backup_codes TEXT NULL,  -- JSON array de códigos hasheados
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    enabled_at TIMESTAMP WITH TIME ZONE NULL,
    
    -- Foreign key constraint
    CONSTRAINT fk_user_two_factor_user_account 
        FOREIGN KEY (user_account_id) 
        REFERENCES app.user_accounts(id) 
        ON DELETE CASCADE
);

-- Crear índices para user_two_factor
CREATE INDEX IF NOT EXISTS idx_user_two_factor_user_account_id 
    ON app.user_two_factor(user_account_id);

-- Comentarios en la tabla
COMMENT ON TABLE app.user_two_factor IS 'Configuración de autenticación de dos factores (2FA) para usuarios';
COMMENT ON COLUMN app.user_two_factor.secret IS 'Secret TOTP en formato base32';
COMMENT ON COLUMN app.user_two_factor.backup_codes IS 'Array JSON de códigos de respaldo hasheados (SHA-256)';
COMMENT ON COLUMN app.user_two_factor.is_enabled IS 'Indica si el 2FA está activado para este usuario';

-- ============================================================================
-- 3. CREAR TABLA user_sessions
-- ============================================================================
-- Rastrea las sesiones activas de los usuarios (tokens JWT)

CREATE TABLE IF NOT EXISTS app.user_sessions (
    id SERIAL PRIMARY KEY,
    user_account_id INTEGER NOT NULL,
    token_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash del token JWT
    device_info VARCHAR(255) NULL,     -- Navegador, OS, etc.
    ip_address VARCHAR(45) NULL,        -- IPv4 o IPv6
    user_agent TEXT NULL,
    location VARCHAR(255) NULL,         -- Ciudad, País
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE NULL,
    
    -- Foreign key constraint
    CONSTRAINT fk_user_sessions_user_account 
        FOREIGN KEY (user_account_id) 
        REFERENCES app.user_accounts(id) 
        ON DELETE CASCADE
);

-- Crear índices para user_sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_account_id 
    ON app.user_sessions(user_account_id);

CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash 
    ON app.user_sessions(token_hash);

CREATE INDEX IF NOT EXISTS idx_user_sessions_is_active 
    ON app.user_sessions(is_active);

-- Comentarios en la tabla
COMMENT ON TABLE app.user_sessions IS 'Sesiones activas de usuarios (tokens JWT)';
COMMENT ON COLUMN app.user_sessions.token_hash IS 'Hash SHA-256 del token JWT para identificación única';
COMMENT ON COLUMN app.user_sessions.is_active IS 'Indica si la sesión está activa o ha sido revocada';

COMMIT;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
-- Verificar que las tablas se crearon correctamente

DO $$
DECLARE
    two_factor_exists BOOLEAN;
    sessions_exists BOOLEAN;
BEGIN
    -- Verificar user_two_factor
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'app' 
        AND table_name = 'user_two_factor'
    ) INTO two_factor_exists;
    
    -- Verificar user_sessions
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'app' 
        AND table_name = 'user_sessions'
    ) INTO sessions_exists;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RESUMEN DE MIGRACIÓN';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'user_two_factor: %', 
        CASE WHEN two_factor_exists THEN '✅ Creado' ELSE '❌ Faltante' END;
    RAISE NOTICE 'user_sessions: %', 
        CASE WHEN sessions_exists THEN '✅ Creado' ELSE '❌ Faltante' END;
    RAISE NOTICE '========================================';
END $$;
