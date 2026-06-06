-- Migration: Create Bookings Table
-- Target: SQLite

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    consultant_id TEXT NOT NULL,
    start_time TEXT NOT NULL,       -- Almacenado como string ISO8601
    end_time TEXT NOT NULL,         -- Almacenado como string ISO8601
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    service TEXT,
    calendar_event_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    reminder_24h_sent INTEGER DEFAULT 0, -- 0 = False, 1 = True
    reminder_1h_sent INTEGER DEFAULT 0,  -- 0 = False, 1 = True
    
    -- Restricción para validar el BookingStatus Enum a nivel de base de datos
    CONSTRAINT fk_status CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'rescheduled')),
    
    -- Claves foráneas (opcionales, recomendadas si usas las otras tablas)
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (consultant_id) REFERENCES consultants(id) ON DELETE CASCADE
);

-- Índices de rendimiento para las búsquedas del ReminderService y LangGraph
CREATE INDEX IF NOT EXISTS idx_bookings_status_time ON bookings (status, start_time);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings (user_id);
