-- Migración para eliminar columnas no utilizadas de team_stats_game
-- Estas columnas no están disponibles en los boxscores JSON actuales

-- Eliminar columnas de tiros (FGM, FGA, 3PM, 3PA, FTM, FTA)
DO $$ 
BEGIN
    -- Eliminar field_goals_made
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'field_goals_made'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN field_goals_made;
        RAISE NOTICE 'Columna field_goals_made eliminada';
    END IF;

    -- Eliminar field_goals_attempted
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'field_goals_attempted'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN field_goals_attempted;
        RAISE NOTICE 'Columna field_goals_attempted eliminada';
    END IF;

    -- Eliminar three_pointers_made
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'three_pointers_made'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN three_pointers_made;
        RAISE NOTICE 'Columna three_pointers_made eliminada';
    END IF;

    -- Eliminar three_pointers_attempted
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'three_pointers_attempted'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN three_pointers_attempted;
        RAISE NOTICE 'Columna three_pointers_attempted eliminada';
    END IF;

    -- Eliminar free_throws_made
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'free_throws_made'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN free_throws_made;
        RAISE NOTICE 'Columna free_throws_made eliminada';
    END IF;

    -- Eliminar free_throws_attempted
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'free_throws_attempted'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN free_throws_attempted;
        RAISE NOTICE 'Columna free_throws_attempted eliminada';
    END IF;

    -- Eliminar offensive_rating
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'offensive_rating'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN offensive_rating;
        RAISE NOTICE 'Columna offensive_rating eliminada';
    END IF;

    -- Eliminar defensive_rating
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'defensive_rating'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN defensive_rating;
        RAISE NOTICE 'Columna defensive_rating eliminada';
    END IF;

    -- Eliminar net_rating
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'espn' 
        AND table_name = 'team_stats_game' 
        AND column_name = 'net_rating'
    ) THEN
        ALTER TABLE espn.team_stats_game DROP COLUMN net_rating;
        RAISE NOTICE 'Columna net_rating eliminada';
    END IF;

    RAISE NOTICE 'Migración completada: columnas no utilizadas eliminadas';
END $$;

