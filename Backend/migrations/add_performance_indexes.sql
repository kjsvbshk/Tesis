-- ============================================================================
-- MIGRACIÓN: Índices de Rendimiento para Optimización
-- ============================================================================
-- Este script agrega índices recomendados para mejorar el rendimiento
-- de las consultas más frecuentes.
--
-- Fecha: 2025-01-XX
-- Fuente: OPTIMIZATION_NOTES.md
-- ============================================================================

BEGIN;

-- ============================================================================
-- Índices para app.user_accounts
-- ============================================================================
-- Los índices UNIQUE ya crean índices automáticamente, pero verificamos por si acaso

DO $$
BEGIN
    -- Índice en username (puede que ya exista por UNIQUE, pero es seguro agregarlo)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'user_accounts' AND indexname = 'idx_user_accounts_username') THEN
        -- Si username es UNIQUE, ya tiene índice, pero lo verificamos
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'app.user_accounts'::regclass AND conname LIKE '%username%' AND contype = 'u') THEN
            CREATE INDEX idx_user_accounts_username ON app.user_accounts(username);
        END IF;
    END IF;
    
    -- Índice en email (similar a username)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'user_accounts' AND indexname = 'idx_user_accounts_email') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'app.user_accounts'::regclass AND conname LIKE '%email%' AND contype = 'u') THEN
            CREATE INDEX idx_user_accounts_email ON app.user_accounts(email);
        END IF;
    END IF;
END $$;

-- ============================================================================
-- Índices para app.user_roles
-- ============================================================================

DO $$
BEGIN
    -- Índice en user_id
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'user_roles' AND indexname = 'idx_user_roles_user_id') THEN
        CREATE INDEX idx_user_roles_user_id ON app.user_roles(user_id);
    END IF;
    
    -- Índice en role_id
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'user_roles' AND indexname = 'idx_user_roles_role_id') THEN
        CREATE INDEX idx_user_roles_role_id ON app.user_roles(role_id);
    END IF;
    
    -- Índice parcial en (user_id, is_active) donde is_active = true
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'user_roles' AND indexname = 'idx_user_roles_active') THEN
        CREATE INDEX idx_user_roles_active ON app.user_roles(user_id, is_active) WHERE is_active = true;
    END IF;
END $$;

-- ============================================================================
-- Índices para espn.bets
-- ============================================================================

DO $$
BEGIN
    -- Índice en user_id
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bets' AND indexname = 'idx_bets_user_id') THEN
        CREATE INDEX idx_bets_user_id ON espn.bets(user_id);
    END IF;
    
    -- Índice en bet_status_code
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bets' AND indexname = 'idx_bets_status') THEN
        CREATE INDEX idx_bets_status ON espn.bets(bet_status_code);
    END IF;
    
    -- Índice compuesto en (user_id, bet_status_code)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bets' AND indexname = 'idx_bets_user_status') THEN
        CREATE INDEX idx_bets_user_status ON espn.bets(user_id, bet_status_code);
    END IF;
END $$;

-- ============================================================================
-- Índices para app.requests
-- ============================================================================

DO $$
BEGIN
    -- Índice en user_id
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'requests' AND indexname = 'idx_requests_user_id') THEN
        CREATE INDEX idx_requests_user_id ON app.requests(user_id);
    END IF;
    
    -- Índice en status
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'requests' AND indexname = 'idx_requests_status') THEN
        CREATE INDEX idx_requests_status ON app.requests(status);
    END IF;
    
    -- Índice en created_at
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'requests' AND indexname = 'idx_requests_created_at') THEN
        CREATE INDEX idx_requests_created_at ON app.requests(created_at);
    END IF;
END $$;

-- ============================================================================
-- Índices para app.predictions
-- ============================================================================
-- Nota: predictions no tiene user_id ni game_id
-- Solo tiene request_id (ya indexado por UNIQUE) y model_version_id (ya indexado)
-- Los índices están cubiertos por las foreign keys existentes

DO $$
BEGIN
    -- Verificar si la tabla existe
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'app' AND table_name = 'predictions') THEN
        -- Solo crear índice en model_version_id si no existe ya
        -- request_id ya tiene índice por UNIQUE constraint
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE schemaname = 'app' 
            AND tablename = 'predictions' 
            AND indexname LIKE '%model_version%'
        ) THEN
            -- Verificar si la columna model_version_id existe y no tiene índice
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'app' 
                AND table_name = 'predictions' 
                AND column_name = 'model_version_id'
            ) THEN
                -- model_version_id ya debería tener índice por ForeignKey con index=True
                -- No creamos índice duplicado
                NULL;
            END IF;
        END IF;
    END IF;
END $$;

-- ============================================================================
-- Índices para app.audit_logs (nota: el nombre de la tabla es 'audit_log')
-- ============================================================================

DO $$
BEGIN
    -- Verificar si la tabla existe
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'app' AND table_name = 'audit_log') THEN
        -- Índice en actor_user_id
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'audit_log' AND indexname = 'idx_audit_actor') THEN
            CREATE INDEX idx_audit_actor ON app.audit_log(actor_user_id);
        END IF;
        
        -- Índice compuesto en (resource_type, resource_id)
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'audit_log' AND indexname = 'idx_audit_resource') THEN
            CREATE INDEX idx_audit_resource ON app.audit_log(resource_type, resource_id);
        END IF;
        
        -- Índice en created_at
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'audit_log' AND indexname = 'idx_audit_created_at') THEN
            CREATE INDEX idx_audit_created_at ON app.audit_log(created_at);
        END IF;
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- Verificación de índices creados
-- ============================================================================
-- Ejecutar para verificar: SELECT * FROM pg_indexes WHERE schemaname IN ('app', 'espn') AND indexname LIKE 'idx_%' ORDER BY schemaname, tablename, indexname;
