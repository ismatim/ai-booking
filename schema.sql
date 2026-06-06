CREATE TABLE users (
    id TEXT PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    name TEXT,
    language TEXT DEFAULT 'en',
    provider TEXT DEFAULT 'twilio',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE consultants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    calendar_id TEXT,
    rate REAL,
    bio TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
, google_refresh_token TEXT, services TEXT DEFAULT '[]', timezone TEXT DEFAULT 'UTC');
CREATE TABLE availability (
    id TEXT PRIMARY KEY,
    consultant_id TEXT REFERENCES consultants(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(consultant_id, day_of_week)
);
CREATE TABLE bookings (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    consultant_id TEXT REFERENCES consultants(id) ON DELETE CASCADE,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT DEFAULT 'confirmed',
    service TEXT,
    notes TEXT,
    calendar_event_id TEXT,
    reminder_24h_sent INTEGER DEFAULT 0,  -- SQLite uses 0/1 for booleans
    reminder_1h_sent INTEGER DEFAULT 0,   -- SQLite uses 0/1 for booleans
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL DEFAULT 'individual',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
, context JSONB DEFAULT '{}');
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, 
    content TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
, session_id TEXT, message TEXT);
CREATE INDEX idx_messages_conversation_id_created_at 
ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_session_id ON messages (session_id);
CREATE INDEX idx_bookings_status_time ON bookings (status, start_time);
CREATE INDEX idx_bookings_user ON bookings (user_id);
