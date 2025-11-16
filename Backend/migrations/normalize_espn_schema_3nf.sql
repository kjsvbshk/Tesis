-- ============================================================================
-- MIGRACIÓN: Normalización del esquema espn hasta 3FN
-- ============================================================================
-- Este script normaliza las tablas del esquema espn hasta la tercera forma normal (3FN)
-- Principalmente enfocado en la tabla bets y otras tablas relacionadas
--
-- Fecha: 2025-01-XX
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. CREAR TABLA DE ODDS NORMALIZADA
-- ============================================================================
-- Las odds deben estar separadas de games porque:
-- - Las odds cambian con el tiempo
-- - Un juego puede tener múltiples sets de odds (histórico)
-- - Las odds dependen del proveedor/bookmaker

-- Verificar si la tabla games existe y tiene columna game_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'espn' AND table_name = 'games'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' AND table_name = 'games' AND column_name = 'game_id'
    ) THEN
        -- Crear tabla con foreign key
        CREATE TABLE IF NOT EXISTS espn.game_odds (
            id SERIAL PRIMARY KEY,
            game_id INTEGER NOT NULL,
            odds_type VARCHAR(20) NOT NULL CHECK (odds_type IN ('moneyline_home', 'moneyline_away', 'spread_home', 'spread_away', 'over_under')),
            odds_value NUMERIC(10, 4) NOT NULL,
            line_value NUMERIC(10, 2), -- Para spread y over/under (ej: -3.5, 220.5)
            provider VARCHAR(50), -- Proveedor de odds (ej: 'espn', 'draftkings', 'fanduel')
            snapshot_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            
            -- Índices para búsquedas rápidas
            CONSTRAINT fk_game_odds_game FOREIGN KEY (game_id) REFERENCES espn.games(game_id) ON DELETE CASCADE
        );
    ELSE
        -- Crear tabla sin foreign key si games no existe o no tiene game_id
        CREATE TABLE IF NOT EXISTS espn.game_odds (
            id SERIAL PRIMARY KEY,
            game_id INTEGER NOT NULL,
            odds_type VARCHAR(20) NOT NULL CHECK (odds_type IN ('moneyline_home', 'moneyline_away', 'spread_home', 'spread_away', 'over_under')),
            odds_value NUMERIC(10, 4) NOT NULL,
            line_value NUMERIC(10, 2), -- Para spread y over/under (ej: -3.5, 220.5)
            provider VARCHAR(50), -- Proveedor de odds (ej: 'espn', 'draftkings', 'fanduel')
            snapshot_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        RAISE NOTICE 'Tabla game_odds creada sin foreign key a games (tabla games no existe o no tiene columna game_id)';
    END IF;
END $$;

-- Crear índices condicionalmente
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'game_odds' AND indexname = 'idx_game_odds_game_id') THEN
        CREATE INDEX idx_game_odds_game_id ON espn.game_odds(game_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'game_odds' AND indexname = 'idx_game_odds_type') THEN
        CREATE INDEX idx_game_odds_type ON espn.game_odds(odds_type);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'game_odds' AND indexname = 'idx_game_odds_snapshot_time') THEN
        CREATE INDEX idx_game_odds_snapshot_time ON espn.game_odds(snapshot_time);
    END IF;
END $$;

-- ============================================================================
-- 2. CREAR TABLA DE BETS NORMALIZADA EN ESQUEMA ESPN
-- ============================================================================
-- La tabla bets se normaliza separando:
-- - Los detalles de la apuesta (bet_details)
-- - La selección de la apuesta (bet_selection)
-- - El estado y resultados (bet_status)

-- Primero, crear tabla de tipos de apuesta (normalización de enum)
CREATE TABLE IF NOT EXISTS espn.bet_types (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

INSERT INTO espn.bet_types (code, name, description) VALUES
    ('moneyline', 'Moneyline', 'Apuesta directa al ganador del partido'),
    ('spread', 'Point Spread', 'Apuesta con margen de puntos'),
    ('over_under', 'Over/Under', 'Apuesta sobre total de puntos')
ON CONFLICT (code) DO NOTHING;

-- Tabla de estados de apuesta (normalización de enum)
CREATE TABLE IF NOT EXISTS espn.bet_statuses (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

INSERT INTO espn.bet_statuses (code, name, description) VALUES
    ('pending', 'Pendiente', 'Apuesta colocada, esperando resultado'),
    ('won', 'Ganada', 'Apuesta ganada'),
    ('lost', 'Perdida', 'Apuesta perdida'),
    ('cancelled', 'Cancelada', 'Apuesta cancelada')
ON CONFLICT (code) DO NOTHING;

-- Tabla principal de apuestas (normalizada)
-- Crear primero sin todas las foreign keys, luego agregarlas condicionalmente
DO $$
BEGIN
    CREATE TABLE IF NOT EXISTS espn.bets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL, -- FK a app.users (sin constraint porque está en otro esquema)
    game_id INTEGER NOT NULL,
    bet_type_code VARCHAR(20) NOT NULL,
    bet_status_code VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Monto de la apuesta (no calculado)
    bet_amount NUMERIC(10, 2) NOT NULL CHECK (bet_amount > 0),
    
    -- Referencia a la odds usada (normalización: no duplicar odds en bets)
    odds_id INTEGER, -- FK a espn.game_odds
    
    -- Odds al momento de la apuesta (snapshot, para auditoría)
    -- Se mantiene por si la odds cambia después
    odds_value NUMERIC(10, 4) NOT NULL,
    
    -- Potential payout se calcula, pero se guarda para auditoría
    -- Es una dependencia transitiva: bet_amount * odds_value
    potential_payout NUMERIC(10, 2) NOT NULL,
    
    -- Timestamps
    placed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints (foreign keys condicionales)
    CONSTRAINT fk_bets_bet_type FOREIGN KEY (bet_type_code) REFERENCES espn.bet_types(code) ON DELETE RESTRICT,
    CONSTRAINT fk_bets_bet_status FOREIGN KEY (bet_status_code) REFERENCES espn.bet_statuses(code) ON DELETE RESTRICT,
    CONSTRAINT chk_bets_payout CHECK (potential_payout >= bet_amount)
    );
    
    -- Agregar foreign keys condicionalmente
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'espn' AND table_name = 'games'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' AND table_name = 'games' AND column_name = 'game_id'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_schema = 'espn' AND table_name = 'bets' AND constraint_name = 'fk_bets_game'
        ) THEN
            ALTER TABLE espn.bets 
            ADD CONSTRAINT fk_bets_game FOREIGN KEY (game_id) REFERENCES espn.games(game_id) ON DELETE RESTRICT;
        END IF;
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'espn' AND table_name = 'game_odds'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_schema = 'espn' AND table_name = 'bets' AND constraint_name = 'fk_bets_odds'
        ) THEN
            ALTER TABLE espn.bets 
            ADD CONSTRAINT fk_bets_odds FOREIGN KEY (odds_id) REFERENCES espn.game_odds(id) ON DELETE SET NULL;
        END IF;
    END IF;
END $$;

-- Crear índices condicionalmente
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bets' AND indexname = 'idx_bets_user_id') THEN
        CREATE INDEX idx_bets_user_id ON espn.bets(user_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bets' AND indexname = 'idx_bets_game_id') THEN
        CREATE INDEX idx_bets_game_id ON espn.bets(game_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bets' AND indexname = 'idx_bets_status') THEN
        CREATE INDEX idx_bets_status ON espn.bets(bet_status_code);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bets' AND indexname = 'idx_bets_placed_at') THEN
        CREATE INDEX idx_bets_placed_at ON espn.bets(placed_at);
    END IF;
END $$;

-- ============================================================================
-- 3. CREAR TABLA DE SELECCIONES DE APUESTA (NORMALIZACIÓN)
-- ============================================================================
-- Separar las selecciones específicas de cada tipo de apuesta
-- Esto evita tener múltiples columnas NULL según el tipo de apuesta

CREATE TABLE IF NOT EXISTS espn.bet_selections (
    id SERIAL PRIMARY KEY,
    bet_id INTEGER NOT NULL,
    
    -- Para moneyline y spread: equipo seleccionado
    selected_team_id INTEGER, -- FK a espn.teams
    
    -- Para spread: valor del spread
    spread_value NUMERIC(10, 2),
    
    -- Para over/under: valor de la línea y si es over o under
    over_under_value NUMERIC(10, 2),
    is_over BOOLEAN,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints (foreign keys condicionales)
    CONSTRAINT fk_bet_selections_bet FOREIGN KEY (bet_id) REFERENCES espn.bets(id) ON DELETE CASCADE,
    
    -- Validaciones lógicas
    CONSTRAINT chk_bet_selections_moneyline CHECK (
        -- Si es moneyline, debe tener selected_team_id y no spread/over_under
        (spread_value IS NULL AND over_under_value IS NULL AND is_over IS NULL) OR
        -- Si es spread, debe tener selected_team_id y spread_value
        (over_under_value IS NULL AND is_over IS NULL) OR
        -- Si es over_under, debe tener over_under_value e is_over
        (selected_team_id IS NULL AND spread_value IS NULL)
    )
);

-- Crear índices condicionalmente
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bet_selections' AND indexname = 'idx_bet_selections_bet_id') THEN
        CREATE INDEX idx_bet_selections_bet_id ON espn.bet_selections(bet_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bet_selections' AND indexname = 'idx_bet_selections_team_id') THEN
        CREATE INDEX idx_bet_selections_team_id ON espn.bet_selections(selected_team_id);
    END IF;
END $$;

-- Agregar foreign key a teams condicionalmente
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'espn' AND table_name = 'teams'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' AND table_name = 'teams' AND column_name = 'team_id'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_schema = 'espn' AND table_name = 'bet_selections' AND constraint_name = 'fk_bet_selections_team'
        ) THEN
            ALTER TABLE espn.bet_selections 
            ADD CONSTRAINT fk_bet_selections_team FOREIGN KEY (selected_team_id) REFERENCES espn.teams(team_id) ON DELETE RESTRICT;
        END IF;
    END IF;
END $$;

-- ============================================================================
-- 4. CREAR TABLA DE RESULTADOS DE APUESTAS (NORMALIZACIÓN)
-- ============================================================================
-- Separar los resultados de las apuestas para mantener historial y auditoría

CREATE TABLE IF NOT EXISTS espn.bet_results (
    id SERIAL PRIMARY KEY,
    bet_id INTEGER NOT NULL UNIQUE, -- Una apuesta tiene un solo resultado
    
    -- Pago real (puede ser diferente al potential_payout si hay ajustes)
    actual_payout NUMERIC(10, 2),
    
    -- Información adicional del resultado
    result_notes TEXT,
    
    -- Timestamps
    settled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_bet_results_bet FOREIGN KEY (bet_id) REFERENCES espn.bets(id) ON DELETE CASCADE,
    CONSTRAINT chk_bet_results_payout CHECK (actual_payout >= 0)
);

-- Crear índices condicionalmente
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bet_results' AND indexname = 'idx_bet_results_bet_id') THEN
        CREATE INDEX idx_bet_results_bet_id ON espn.bet_results(bet_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'espn' AND tablename = 'bet_results' AND indexname = 'idx_bet_results_settled_at') THEN
        CREATE INDEX idx_bet_results_settled_at ON espn.bet_results(settled_at);
    END IF;
END $$;

-- ============================================================================
-- 5. MIGRAR DATOS DE ODDS DESDE games A game_odds
-- ============================================================================
-- Si existen odds en la tabla games, migrarlas a game_odds

DO $$
BEGIN
    -- Verificar si la tabla games existe y tiene las columnas necesarias
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'espn' AND table_name = 'games'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' AND table_name = 'games' AND column_name = 'game_id'
    ) THEN
        -- Migrar home_odds si existe la columna
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'espn' AND table_name = 'games' AND column_name = 'home_odds'
        ) THEN
            INSERT INTO espn.game_odds (game_id, odds_type, odds_value, provider, snapshot_time)
            SELECT 
                g.game_id,
                'moneyline_home' as odds_type,
                g.home_odds::NUMERIC(10, 4) as odds_value,
                'espn' as provider,
                COALESCE(g.updated_at, g.created_at, CURRENT_TIMESTAMP) as snapshot_time
            FROM espn.games g
            WHERE g.home_odds IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM espn.game_odds 
                WHERE game_id = g.game_id AND odds_type = 'moneyline_home' AND provider = 'espn'
            );
        END IF;
        
        -- Migrar away_odds si existe la columna
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'espn' AND table_name = 'games' AND column_name = 'away_odds'
        ) THEN
            INSERT INTO espn.game_odds (game_id, odds_type, odds_value, provider, snapshot_time)
            SELECT 
                g.game_id,
                'moneyline_away' as odds_type,
                g.away_odds::NUMERIC(10, 4) as odds_value,
                'espn' as provider,
                COALESCE(g.updated_at, g.created_at, CURRENT_TIMESTAMP) as snapshot_time
            FROM espn.games g
            WHERE g.away_odds IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM espn.game_odds 
                WHERE game_id = g.game_id AND odds_type = 'moneyline_away' AND provider = 'espn'
            );
        END IF;
        
        -- Migrar over_under si existe la columna
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'espn' AND table_name = 'games' AND column_name = 'over_under'
        ) THEN
            INSERT INTO espn.game_odds (game_id, odds_type, line_value, provider, snapshot_time)
            SELECT 
                g.game_id,
                'over_under' as odds_type,
                g.over_under::NUMERIC(10, 2) as line_value,
                'espn' as provider,
                COALESCE(g.updated_at, g.created_at, CURRENT_TIMESTAMP) as snapshot_time
            FROM espn.games g
            WHERE g.over_under IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM espn.game_odds 
                WHERE game_id = g.game_id AND odds_type = 'over_under' AND provider = 'espn'
            );
        END IF;
        
        RAISE NOTICE 'Datos de odds migrados desde espn.games a espn.game_odds';
    ELSE
        RAISE NOTICE 'Tabla espn.games no existe o no tiene columna game_id, omitiendo migración de odds';
    END IF;
END $$;

-- ============================================================================
-- 6. MIGRAR DATOS DE BETS DESDE app.bets A espn.bets (SI EXISTE)
-- ============================================================================
-- Si existe la tabla app.bets, migrar los datos a la nueva estructura normalizada

DO $$
BEGIN
    -- Verificar si existe la tabla app.bets
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'app' AND table_name = 'bets') THEN
        
        -- Migrar apuestas
        INSERT INTO espn.bets (
            id, user_id, game_id, bet_type_code, bet_status_code,
            bet_amount, odds_value, potential_payout,
            placed_at, settled_at, created_at, updated_at
        )
        SELECT 
            b.id,
            b.user_id,
            b.game_id,
            CASE 
                WHEN b.bet_type::text = 'moneyline' THEN 'moneyline'
                WHEN b.bet_type::text = 'spread' THEN 'spread'
                WHEN b.bet_type::text = 'over_under' THEN 'over_under'
                ELSE 'moneyline'
            END as bet_type_code,
            CASE 
                WHEN b.status::text = 'pending' THEN 'pending'
                WHEN b.status::text = 'won' THEN 'won'
                WHEN b.status::text = 'lost' THEN 'lost'
                WHEN b.status::text = 'cancelled' THEN 'cancelled'
                ELSE 'pending'
            END as bet_status_code,
            b.bet_amount,
            b.odds,
            b.potential_payout,
            b.placed_at,
            b.settled_at,
            b.created_at,
            b.updated_at
        FROM app.bets b
        WHERE NOT EXISTS (SELECT 1 FROM espn.bets WHERE id = b.id);
        
        -- Migrar selecciones de apuestas
        INSERT INTO espn.bet_selections (
            bet_id, selected_team_id, spread_value, over_under_value, is_over
        )
        SELECT 
            b.id as bet_id,
            b.selected_team_id,
            b.spread_value,
            b.over_under_value,
            b.is_over
        FROM app.bets b
        WHERE (b.selected_team_id IS NOT NULL 
           OR b.spread_value IS NOT NULL 
           OR b.over_under_value IS NOT NULL)
          AND NOT EXISTS (SELECT 1 FROM espn.bet_selections WHERE bet_id = b.id);
        
        -- Migrar resultados de apuestas
        INSERT INTO espn.bet_results (
            bet_id, actual_payout, settled_at
        )
        SELECT 
            b.id as bet_id,
            b.actual_payout,
            b.settled_at
        FROM app.bets b
        WHERE (b.actual_payout IS NOT NULL OR b.settled_at IS NOT NULL)
          AND NOT EXISTS (SELECT 1 FROM espn.bet_results WHERE bet_id = b.id);
        
        RAISE NOTICE 'Datos migrados desde app.bets a espn.bets';
    ELSE
        RAISE NOTICE 'Tabla app.bets no existe, omitiendo migración';
    END IF;
END $$;

-- ============================================================================
-- 7. CREAR FUNCIÓN PARA CALCULAR POTENTIAL_PAYOUT (AUDITORÍA)
-- ============================================================================
-- Función para validar que potential_payout = bet_amount * odds_value

CREATE OR REPLACE FUNCTION espn.calculate_potential_payout(
    p_bet_amount NUMERIC,
    p_odds_value NUMERIC
) RETURNS NUMERIC AS $$
BEGIN
    RETURN ROUND(p_bet_amount * p_odds_value, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger para validar potential_payout
CREATE OR REPLACE FUNCTION espn.validate_bet_payout()
RETURNS TRIGGER AS $$
DECLARE
    calculated_payout NUMERIC;
BEGIN
    calculated_payout := espn.calculate_potential_payout(NEW.bet_amount, NEW.odds_value);
    
    IF ABS(NEW.potential_payout - calculated_payout) > 0.01 THEN
        RAISE WARNING 'potential_payout (%) no coincide con cálculo (bet_amount * odds_value = %)', 
            NEW.potential_payout, calculated_payout;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger condicionalmente
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trigger_validate_bet_payout' 
        AND tgrelid = 'espn.bets'::regclass
    ) THEN
        CREATE TRIGGER trigger_validate_bet_payout
            BEFORE INSERT OR UPDATE ON espn.bets
            FOR EACH ROW
            EXECUTE FUNCTION espn.validate_bet_payout();
    END IF;
END $$;

-- ============================================================================
-- 8. CREAR VISTAS PARA FACILITAR CONSULTAS (OPCIONAL)
-- ============================================================================

-- Vista completa de apuestas con toda la información relacionada
-- Crear solo si las tablas necesarias existen
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'espn' AND table_name = 'bets'
    ) THEN
        -- Intentar crear la vista, si falla por tablas faltantes, simplemente no crearla
        BEGIN
            CREATE OR REPLACE VIEW espn.bets_full AS
            SELECT 
                b.id,
                b.user_id,
                b.game_id,
                g.espn_id as game_espn_id,
                bt.name as bet_type_name,
                bst.name as bet_status_name,
                b.bet_amount,
                b.odds_value,
                b.potential_payout,
                bsel.selected_team_id,
                t.name as selected_team_name,
                bsel.spread_value,
                bsel.over_under_value,
                bsel.is_over,
                br.actual_payout,
                b.placed_at,
                b.settled_at,
                b.created_at,
                b.updated_at
            FROM espn.bets b
            LEFT JOIN espn.bet_types bt ON b.bet_type_code = bt.code
            LEFT JOIN espn.bet_statuses bst ON b.bet_status_code = bst.code
            LEFT JOIN espn.bet_selections bsel ON b.id = bsel.bet_id
            LEFT JOIN espn.bet_results br ON b.id = br.bet_id
            LEFT JOIN espn.games g ON b.game_id = g.game_id
            LEFT JOIN espn.teams t ON bsel.selected_team_id = t.team_id;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'No se pudo crear la vista bets_full: %', SQLERRM;
        END;
    END IF;
END $$;

-- ============================================================================
-- 9. COMENTARIOS Y DOCUMENTACIÓN
-- ============================================================================

COMMENT ON TABLE espn.game_odds IS 'Odds históricas de partidos, normalizadas para soportar múltiples proveedores y snapshots temporales';
COMMENT ON TABLE espn.bets IS 'Apuestas de usuarios, normalizada hasta 3FN separando tipos, estados, selecciones y resultados';
COMMENT ON TABLE espn.bet_selections IS 'Selecciones específicas de cada apuesta (equipo, spread, over/under)';
COMMENT ON TABLE espn.bet_results IS 'Resultados y pagos de apuestas, separados para auditoría';
COMMENT ON TABLE espn.bet_types IS 'Catálogo de tipos de apuestas disponibles';
COMMENT ON TABLE espn.bet_statuses IS 'Catálogo de estados de apuestas';

COMMENT ON COLUMN espn.bets.potential_payout IS 'Pago potencial calculado (bet_amount * odds_value). Se guarda para auditoría aunque sea calculable.';
COMMENT ON COLUMN espn.bets.odds_id IS 'Referencia a game_odds usada. NULL si la odds no está en game_odds.';
COMMENT ON COLUMN espn.bets.odds_value IS 'Snapshot de la odds al momento de la apuesta, para auditoría.';

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================

COMMIT;

-- ============================================================================
-- NOTAS POST-MIGRACIÓN:
-- ============================================================================
-- 1. Las columnas home_odds, away_odds, over_under en espn.games pueden
--    mantenerse para compatibilidad, pero se recomienda usar game_odds
-- 2. La tabla app.bets puede mantenerse o eliminarse según necesidad
-- 3. Actualizar los modelos de SQLAlchemy para reflejar la nueva estructura
-- 4. Actualizar los servicios y endpoints que usan bets
-- ============================================================================

