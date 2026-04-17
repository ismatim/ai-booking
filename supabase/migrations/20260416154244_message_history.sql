-- 1. Remove the old, non-relational table
DROP TABLE IF EXISTS conversation_history;

-- 2. Create the Pro Relational structure
-- Table for Chat Rooms / Individual Chats
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL DEFAULT 'individual',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, 
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create an index for speed (we fetch history by time)
-- The Performance Engine 
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id_created_at 
ON messages(conversation_id, created_at DESC);
