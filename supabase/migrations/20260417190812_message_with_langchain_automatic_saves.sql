ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS session_id TEXT,
ADD COLUMN IF NOT EXISTS message JSONB;

-- Create an index to make history lookups lightning fast
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages (session_id);
