-- ============================================================================
-- Remove foreign key constraint from app.transactions.bet_id
-- ============================================================================
-- The bet_id column in app.transactions should reference espn.bets.id,
-- but we cannot have a cross-schema foreign key constraint in PostgreSQL.
-- We'll keep bet_id as a regular integer column without FK constraint.

DO $$
BEGIN
    -- Drop the foreign key constraint if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'app' 
        AND table_name = 'transactions' 
        AND constraint_name = 'transactions_bet_id_fkey'
    ) THEN
        ALTER TABLE app.transactions 
        DROP CONSTRAINT transactions_bet_id_fkey;
        
        RAISE NOTICE 'Foreign key constraint transactions_bet_id_fkey dropped from app.transactions';
    ELSE
        RAISE NOTICE 'Foreign key constraint transactions_bet_id_fkey does not exist, skipping';
    END IF;
    
    -- Also check for other possible constraint names
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'app' 
        AND table_name = 'transactions' 
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%bet_id%'
    ) THEN
        -- Get the constraint name and drop it
        DECLARE
            constraint_name_var TEXT;
        BEGIN
            SELECT constraint_name INTO constraint_name_var
            FROM information_schema.table_constraints 
            WHERE constraint_schema = 'app' 
            AND table_name = 'transactions' 
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name LIKE '%bet_id%'
            LIMIT 1;
            
            IF constraint_name_var IS NOT NULL THEN
                EXECUTE format('ALTER TABLE app.transactions DROP CONSTRAINT %I', constraint_name_var);
                RAISE NOTICE 'Foreign key constraint % dropped from app.transactions', constraint_name_var;
            END IF;
        END;
    END IF;
END $$;

