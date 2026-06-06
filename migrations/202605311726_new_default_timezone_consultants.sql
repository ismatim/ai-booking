-- 1. Desactivamos temporalmente las llaves foráneas para evitar bloqueos
PRAGMA foreign_keys=OFF;

-- 2. Creamos una tabla idéntica pero con el nuevo DEFAULT deseado
CREATE TABLE consultants_new (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    calendar_id TEXT,
    rate REAL,
    bio TEXT,
    google_refresh_token TEXT,
    services TEXT DEFAULT '[]',
    timezone TEXT DEFAULT 'America/Argentina/Buenos_Aires', -- 🌟 El nuevo default
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 3. Migramos todos los datos de la vieja tabla a la nueva
INSERT INTO consultants_new (id, name, email, calendar_id, rate, bio, google_refresh_token, services, timezone, created_at)
SELECT id, name, email, calendar_id, rate, bio, google_refresh_token, services, timezone, created_at 
FROM consultants;

-- 4. Actualizamos de paso a los consultores viejos que decían 'UTC' para que tengan Buenos Aires
UPDATE consultants_new SET timezone = 'America/Argentina/Buenos_Aires' WHERE timezone = 'UTC';

-- 5. Eliminamos la tabla vieja
DROP TABLE consultants;

-- 6. Renombramos la nueva tabla al nombre original
ALTER TABLE consultants_new RENAME TO consultants;

-- 7. Volvemos a encender las llaves foráneas
PRAGMA foreign_keys=ON;
