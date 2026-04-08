import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# The SQL schema we discussed earlier
SCHEMA_SQL = """
-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT UNIQUE NOT NULL,
    name TEXT,
    language TEXT DEFAULT 'en',
    provider TEXT DEFAULT 'twilio',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Consultants Table
CREATE TABLE IF NOT EXISTS consultants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    calendar_id TEXT,
    rate DECIMAL(10, 2),
    bio TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Availability Table
CREATE TABLE IF NOT EXISTS availability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultant_id UUID REFERENCES consultants(id) ON DELETE CASCADE,
    day_of_week INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(consultant_id, day_of_week)
);

-- 4. Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    consultant_id UUID REFERENCES consultants(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'confirmed',
    service TEXT,
    notes TEXT,
    calendar_event_id TEXT,
    reminder_24h_sent BOOLEAN DEFAULT FALSE,
    reminder_1h_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Conversation History Table
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    messages JSONB DEFAULT '[]'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""


def setup_database():
    conn_string = os.getenv("SUPABASE_CONN")
    if not conn_string:
        print("❌ Error: SUPABASE_CONN not found in .env")
        return

    print("🛠️ Connecting to PostgreSQL to build schema...")
    try:
        # Connect to the database
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor()

        # Execute the schema creation
        cur.execute(SCHEMA_SQL)

        # Commit the changes
        conn.commit()

        print("✅ Schema created successfully! All tables and fields are ready.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Failed to build schema: {e}")


if __name__ == "__main__":
    setup_database()
