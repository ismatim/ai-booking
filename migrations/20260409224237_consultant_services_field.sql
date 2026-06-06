-- Add the services column if it doesn't exist
ALTER TABLE consultants 
ADD COLUMN IF NOT EXISTS services TEXT[] DEFAULT '{}';

-- Optional: Add a check to ensure the array isn't empty at the DB level
ALTER TABLE consultants 
ADD CONSTRAINT services_not_empty CHECK (array_length(services, 1) > 0);
