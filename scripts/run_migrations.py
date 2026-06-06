import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "app.db"
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def ensure_migration_table(conn: sqlite3.Connection):
    """Creates the internal metadata tracking table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()


def get_applied_migrations(conn: sqlite3.Connection) -> set:
    """Returns a set of all migration filenames already executed."""
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cursor.fetchall()}


def run_migrations():
    print("🚀 Starting SQLite migration pipeline...")

    if not MIGRATIONS_DIR.exists():
        print(f"❌ Error: Migrations directory missing at {MIGRATIONS_DIR}")
        return

    # Gather and sort all local .sql migration files sequentially
    migration_files = sorted([f for f in MIGRATIONS_DIR.glob("*.sql")])
    if not migration_files:
        print("ℹ️ No migration files found.")
        return

    conn = get_db_connection()
    ensure_migration_table(conn)
    applied_versions = get_applied_migrations(conn)

    # Iterate through files and execute unapplied updates
    for file_path in migration_files:
        filename = file_path.name

        if filename in applied_versions:
            # Skip files that have already been executed
            continue

        print(f"🛠️ Applying migration: {filename}...")

        with open(file_path, "r") as f:
            migration_sql = f.read()

        # Wrap each individual file deployment inside an atomic transaction
        try:
            with conn:  # Enters an implicit transaction block
                # Execute the DDL statements
                conn.executescript(migration_sql)

                # Record this file as successfully completed
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)", (filename,)
                )
            print(f"✅ Successfully applied {filename}")
        except sqlite3.Error as e:
            print(f"💥 Migration failed on {filename}! Rolling back changes.")
            print(f"Error Details: {e}")
            conn.close()
            return

    conn.close()
    print("🎉 All migrations are up to date!")


if __name__ == "__main__":
    run_migrations()
