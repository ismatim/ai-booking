# scripts/seed_db.py
import os
import sys
import sqlite3
import uuid
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import get_settings

settings = get_settings()

DB_PATH = os.path.join(BASE_DIR, settings.database_filename)


def seed_database():
    print(f"🗄️ Connecting to database at: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(
            "❌ Error: app.db does not exist. Please run your database initialization or migrations first."
        )
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    try:
        print("🧹 Cleaning old data to prevent UNIQUE constraint collisions...")
        cursor.execute("DELETE FROM messages;")
        cursor.execute("DELETE FROM conversations;")
        cursor.execute("DELETE FROM bookings;")
        cursor.execute("DELETE FROM availability;")
        cursor.execute("DELETE FROM consultants;")
        cursor.execute("DELETE FROM users;")

        # ==================================================================
        # 1. SEED CONSULTANTS (Refactored to use generated UUIDs)
        # ==================================================================
        print("👥 Seeding consultants...")

        # Pre-generate unique ID strings to bind dependencies downstream
        ana_id = str(uuid.uuid4())
        carlos_id = str(uuid.uuid4())

        consultant_data = [
            (
                ana_id,  # Primary Key UUID v4
                "Ana Martínez",
                "ana.martinez@broker.com",
                "cal_ana_99283",
                150.0,
                "10+ years experience in digital portfolios and volatility hedging.",
                "refresh_token_ana_xyz123",
                json.dumps(["Crypto Assets", "Risk Management"]),
                "America/Argentina/Buenos_Aires",
            ),
            (
                carlos_id,  # Primary Key UUID v4
                "Carlos Gómez",
                "carlos.gomez@broker.com",
                "cal_carlos_55124",
                180.0,
                "Former Wall Street analyst specializing in long-term retirement portfolios.",
                "refresh_token_carlos_abc789",
                json.dumps(
                    ["Traditional Stock Market", "Bonds", "Retirement Planning"]
                ),
                "America/New_York",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO consultants (id, name, email, calendar_id, rate, bio, google_refresh_token, services, timezone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
            consultant_data,
        )

        # ==================================================================
        # 2. SEED AVAILABILITY (Mon = 1 to Fri = 5)
        # ==================================================================
        print("🗓️ Seeding consultant availability grids...")
        availability_data = []

        # Set 9 AM to 5 PM availability for weekdays matching runtime UUIDs
        for c_id in [ana_id, carlos_id]:
            for day in range(1, 6):  # Monday to Friday
                availability_data.append(
                    (str(uuid.uuid4()), c_id, day, "09:00 AM", "05:00 PM")
                )

        cursor.executemany(
            """
            INSERT INTO availability (id, consultant_id, day_of_week, start_time, end_time)
            VALUES (?, ?, ?, ?, ?);
        """,
            availability_data,
        )

        # ==================================================================
        # 3. SEED USERS
        # ==================================================================
        print("📱 Seeding mock users...")

        user_juan_id = "u-juan-perez-7721"
        user_maria_id = str(uuid.uuid4())

        users_data = [
            (user_juan_id, "+541112345678", "Juan Perez", "en", "twilio"),
            (user_maria_id, "+14155552671", "Maria Lopez", "en", "twilio"),
        ]

        cursor.executemany(
            """
            INSERT INTO users (id, phone_number, name, language, provider)
            VALUES (?, ?, ?, ?, ?);
        """,
            users_data,
        )

        # ==================================================================
        # 4. SEED CONVERSATIONS & MESSAGES
        # ==================================================================
        print("💬 Seeding interaction history channels...")

        conv_juan_id = "c-juan-conv-001"
        conv_maria_id = str(uuid.uuid4())

        conversations_data = [
            (
                conv_juan_id,
                "whatsapp:+541112345678",
                "individual",
                json.dumps({"active_node": "concierge"}),
            ),
            (
                conv_maria_id,
                "whatsapp:+14155552671",
                "individual",
                json.dumps({"active_node": "book"}),
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO conversations (id, external_id, type, context)
            VALUES (?, ?, ?, ?);
        """,
            conversations_data,
        )

        # Message exchange records
        messages_data = [
            (str(uuid.uuid4()), conv_juan_id, "user", "Hello", "session-juan-abc"),
            (
                str(uuid.uuid4()),
                conv_juan_id,
                "assistant",
                "Hello Juan Perez! I'm your concierge. I can answer questions or help you get an appointment.",
                "session-juan-abc",
            ),
            (
                str(uuid.uuid4()),
                conv_juan_id,
                "user",
                "I want an appointment with Ana",
                "session-juan-abc",
            ),
            (
                str(uuid.uuid4()),
                conv_maria_id,
                "user",
                "Hi, what does Carlos do?",
                "session-maria-xyz",
            ),
            (
                str(uuid.uuid4()),
                conv_maria_id,
                "assistant",
                "Carlos is a former Wall Street analyst specializing in traditional stock markets and bonds.",
                "session-maria-xyz",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO messages (id, conversation_id, role, content, session_id)
            VALUES (?, ?, ?, ?, ?);
        """,
            messages_data,
        )

        # ==================================================================
        # 5. SEED BOOKINGS (Matches our Reschedule Agent Mock)
        # ==================================================================
        print("💾 Seeding active appointment entries...")

        bookings_data = [
            (
                "BK-2026-9874",  # Matches the ID your RescheduleAgent expects
                user_juan_id,
                ana_id,  # Relational link mapped to Ana's valid UUID variable
                "2026-06-01 09:00:00",  # Explicit upcoming date (Monday)
                "2026-06-01 10:00:00",
                "confirmed",
                "Crypto Assets",
                "Initial strategy review for volatile asset portfolio hedging.",
                "evt_gcal_99812a",
                0,
                0,
            )
        ]

        cursor.executemany(
            """
            INSERT INTO bookings (id, user_id, consultant_id, start_time, end_time, status, service, notes, calendar_event_id, reminder_24h_sent, reminder_1h_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
            bookings_data,
        )

        # Commit everything to file
        conn.commit()
        print("\n🎉 Database successfully seeded with transactional datasets!")

    except Exception as e:
        conn.rollback()
        print(f"\n💥 Database seeding failed! Rolling back changes. Error: {e}")
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()
