-- This "DO" block makes the migration idempotent (safe to run multiple times)
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='consultants' AND column_name='calendar_id'
    ) THEN
        ALTER TABLE consultants ADD COLUMN calendar_id TEXT;
        
        -- Add a comment to describe the column in the Supabase UI
        COMMENT ON COLUMN consultants.calendar_id IS 'The Google Calendar ID used for checking consultant availability.';
    END IF;
END $$;
