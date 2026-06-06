"""Database service class interacting with the unified async SQLite singleton."""

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from cryptography.fernet import Fernet

from config import get_settings
from database import get_db
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class DatabaseService:
    def __init__(self):
        self.cipher = Fernet(settings.encryption_key.encode())

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def get_or_create_user(
        self, phone_number: str, name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch an existing user by phone or create a new one asynchronously."""
        user = await self.get_user_by_phone(phone_number)
        if user:
            return user

        user_id = str(uuid4())
        db_manager = get_db()
        conn = await db_manager.get_connection()

        await conn.execute(
            "INSERT INTO users (id, phone_number, name) VALUES (?, ?, ?)",
            (user_id, phone_number, name),
        )
        await conn.commit()

        logger.info("Created new user (id assigned programmatically via UUID)")
        fetched_user = await self.get_user_by_id(user_id)
        return dict(fetched_user) if fetched_user else {}

    async def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Fetch a user by phone number using the async connection.

        Handles both E.164 formats with or without the leading '+' sign dynamically.
        """
        db_manager = get_db()
        conn = await db_manager.get_connection()

        clean_digits = re.sub(r"\D", "", phone_number)  # Example: "14155552671"
        phone_with_plus = f"+{clean_digits}"  # Example: "+14155552671"

        async with conn.execute(
            "SELECT * FROM users WHERE phone_number = ? OR phone_number = ?",
            (clean_digits, phone_with_plus),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a user by UUID using the async connection."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_user(
        self, user_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update user fields dynamically using the async connection."""
        if not data:
            return await self.get_user_by_id(user_id)

        keys = data.keys()
        set_clause = ", ".join([f"{k} = ?" for k in keys])
        values = list(data.values()) + [user_id]

        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        await conn.commit()

        return await self.get_user_by_id(user_id)

    # ------------------------------------------------------------------
    # Consultants
    # ------------------------------------------------------------------

    async def get_all_consultants(self) -> List[Dict[str, Any]]:
        """Return all consultants using the async connection."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute("SELECT * FROM consultants") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_consultant_by_id(
        self, consultant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a consultant by UUID."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            "SELECT * FROM consultants WHERE id = ?", (consultant_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_consultant(self, consultant_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single consultant by their UUID asynchronously."""
        try:
            return await self.get_consultant_by_id(consultant_id)
        except Exception as e:
            logger.error(f"Error fetching consultant {consultant_id}: {e}")
            return None

    async def create_consultant(self, data: Any) -> Dict[str, Any]:
        """Insert a new consultant record asynchronously."""
        payload = (
            data.model_dump(exclude_none=True) if hasattr(data, "model_dump") else data
        )
        if "id" not in payload:
            payload["id"] = str(uuid4())

        keys = payload.keys()
        columns = ", ".join(keys)
        placeholders = ", ".join(["?" for _ in keys])

        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(
            f"INSERT INTO consultants ({columns}) VALUES ({placeholders})",
            list(payload.values()),
        )
        await conn.commit()

        logger.info("Created consultant: %s", payload.get("name"))
        fetched = await self.get_consultant_by_id(payload["id"])
        return dict(fetched) if fetched else {}

    async def update_consultant(
        self, consultant_id: str, data: Any
    ) -> Optional[Dict[str, Any]]:
        """Update consultant fields dynamically."""
        payload = (
            data.model_dump(exclude_none=True) if hasattr(data, "model_dump") else data
        )
        if not payload:
            return await self.get_consultant_by_id(consultant_id)

        keys = payload.keys()
        set_clause = ", ".join([f"{k} = ?" for k in keys])
        values = list(payload.values()) + [consultant_id]

        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(f"UPDATE consultants SET {set_clause} WHERE id = ?", values)
        await conn.commit()

        return await self.get_consultant_by_id(consultant_id)

    async def delete_consultant(self, consultant_id: str) -> bool:
        """Delete a consultant by UUID asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute("DELETE FROM consultants WHERE id = ?", (consultant_id,))
        await conn.commit()
        return True

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    async def get_availability_for_day(
        self, consultant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch the working hours for a specific consultant asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            "SELECT start_time, end_time FROM availability WHERE consultant_id = ?",
            (consultant_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_availability(self, data: Any) -> Dict[str, Any]:
        """Upsert an availability record asynchronously."""
        row_id = str(uuid4())
        consultant_id = str(data.consultant_id)
        day_of_week = (
            data.day_of_week.value
            if hasattr(data.day_of_week, "value")
            else data.day_of_week
        )
        start_time = (
            data.start_time.isoformat()
            if hasattr(data.start_time, "isoformat")
            else data.start_time
        )
        end_time = (
            data.end_time.isoformat()
            if hasattr(data.end_time, "isoformat")
            else data.end_time
        )

        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(
            """
            INSERT INTO availability (id, consultant_id, day_of_week, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(consultant_id, day_of_week) DO UPDATE SET
                start_time = excluded.start_time,
                end_time = excluded.end_time
            """,
            (row_id, consultant_id, day_of_week, start_time, end_time),
        )
        await conn.commit()

        async with conn.execute(
            "SELECT * FROM availability WHERE consultant_id = ? AND day_of_week = ?",
            (consultant_id, day_of_week),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

    async def delete_availability(self, availability_id: str) -> bool:
        """Delete an availability slot by UUID asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute("DELETE FROM availability WHERE id = ?", (availability_id,))
        await conn.commit()
        return True

    # ------------------------------------------------------------------
    # Bookings
    # ------------------------------------------------------------------

    async def create_booking(self, data: Any) -> Dict[str, Any]:
        """Insert a new booking record asynchronously."""
        booking_id = str(uuid4())
        payload = {
            "id": booking_id,
            "user_id": str(data.user_id),
            "consultant_id": str(data.consultant_id),
            "start_time": data.start_time.isoformat()
            if hasattr(data.start_time, "isoformat")
            else data.start_time,
            "end_time": data.end_time.isoformat()
            if hasattr(data.end_time, "isoformat")
            else data.end_time,
            "status": "confirmed",
        }
        if getattr(data, "notes", None):
            payload["notes"] = data.notes
        if getattr(data, "service", None):
            payload["service"] = data.service

        keys = payload.keys()
        columns = ", ".join(keys)
        placeholders = ", ".join(["?" for _ in keys])

        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(
            f"INSERT INTO bookings ({columns}) VALUES ({placeholders})",
            list(payload.values()),
        )
        await conn.commit()

        logger.info("Created booking for user %s", data.user_id)
        fetched = await self.get_booking_by_id(booking_id)
        return dict(fetched) if fetched else {}

    async def get_booking_by_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a booking by UUID asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            "SELECT * FROM bookings WHERE id = ?", (booking_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                res = dict(row)
                res["reminder_24h_sent"] = bool(res["reminder_24h_sent"])
                res["reminder_1h_sent"] = bool(res["reminder_1h_sent"])
                return res
            return None

    async def get_bookings_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all bookings for a given user asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            "SELECT * FROM bookings WHERE user_id = ? ORDER BY start_time DESC",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_bookings_by_consultant(
        self, consultant_id: str
    ) -> List[Dict[str, Any]]:
        """Return all bookings for a given consultant."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            "SELECT * FROM bookings WHERE consultant_id = ? ORDER BY start_time DESC",
            (consultant_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_upcoming_bookings(
        self, from_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Return confirmed bookings with start_time in the future asynchronously."""
        if from_time is None:
            from_time = datetime.now(timezone.utc)

        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            """
            SELECT * FROM bookings 
            WHERE status = 'confirmed' AND start_time >= ? 
            ORDER BY start_time ASC
            """,
            (from_time.isoformat(),),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_booking(
        self, booking_id: str, data: Any
    ) -> Optional[Dict[str, Any]]:
        """Update booking fields asynchronously."""
        payload: Dict[str, Any] = {}
        if getattr(data, "start_time", None):
            payload["start_time"] = data.start_time.isoformat()
        if getattr(data, "end_time", None):
            payload["end_time"] = data.end_time.isoformat()
        if getattr(data, "status", None):
            payload["status"] = (
                data.status.value if hasattr(data.status, "value") else data.status
            )
        if getattr(data, "notes", None) is not None:
            payload["notes"] = data.notes

        if not payload:
            return await self.get_booking_by_id(booking_id)

        keys = payload.keys()
        set_clause = ", ".join([f"{k} = ?" for k in keys])
        values = list(payload.values()) + [booking_id]

        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(f"UPDATE bookings SET {set_clause} WHERE id = ?", values)
        await conn.commit()

        return await self.get_booking_by_id(booking_id)

    async def cancel_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Mark a booking as cancelled asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
        )
        await conn.commit()
        return await self.get_booking_by_id(booking_id)

    async def set_calendar_event_id(self, booking_id: str, event_id: str) -> None:
        """Store the Google Calendar event ID on a booking asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(
            "UPDATE bookings SET calendar_event_id = ? WHERE id = ?",
            (event_id, booking_id),
        )
        await conn.commit()

    # ------------------------------------------------------------------
    # Conversation history & Turn-by-Turn State Tracking
    # ------------------------------------------------------------------

    async def get_or_create_conversation(
        self, external_id: str, chat_type: str = "individual"
    ) -> Dict[str, Any]:
        """Finds or creates the conversation record asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()

        async with conn.execute(
            "SELECT * FROM conversations WHERE external_id = ?", (external_id,)
        ) as cursor:
            row = await cursor.fetchone()

        logger.info(
            f"get_or_create_conversation: external_id={external_id}, chat_type={chat_type}"
        )

        if row:
            res = dict(row)
            res["context"] = json.loads(res["context"]) if res["context"] else {}
            return res

        conv_id = str(uuid4())
        empty_context = json.dumps({})
        await conn.execute(
            "INSERT INTO conversations (id, external_id, type, context) VALUES (?, ?, ?, ?)",
            (conv_id, external_id, chat_type, empty_context),
        )
        await conn.commit()

        async with conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ) as cursor:
            res = dict(await cursor.fetchone())
            res["context"] = json.loads(res["context"]) if res["context"] else {}
            return res

    async def get_messages(
        self, conversation_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """By-pass handler: Fetches manually tracked backup text items."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            """
            SELECT role, content FROM messages 
            WHERE conversation_id = ? 
            ORDER BY created_at DESC LIMIT ?
            """,
            (conversation_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows][::-1]

    async def save_message(self, conversation_id: str, role: str, content: str) -> None:
        """Inserts a fallback trace message row asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        await conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        await conn.commit()

    async def update_user_context(
        self, identifier: str, updates: dict
    ) -> Optional[Any]:
        """Merges new turns into the persistent context block inside SQLite."""
        try:
            if not identifier:
                logger.error(
                    "Error: No identifier (phone) provided to update_user_context"
                )
                return None

            db_manager = get_db()
            conn = await db_manager.get_connection()

            async with conn.execute(
                "SELECT context FROM conversations WHERE external_id = ?", (identifier,)
            ) as cursor:
                row = await cursor.fetchone()

            current_context = {}
            if row and row["context"]:
                current_context = json.loads(row["context"])

            new_context = {**current_context, **updates}
            serialized_context = json.dumps(new_context)

            conv_id = str(uuid4())
            await conn.execute(
                """
                INSERT INTO conversations (id, external_id, type, context) 
                VALUES (?, ?, 'individual', ?)
                ON CONFLICT(external_id) DO UPDATE SET context = excluded.context
                """,
                (conv_id, identifier, serialized_context),
            )
            await conn.commit()

            async with conn.execute(
                "SELECT * FROM conversations WHERE external_id = ?", (identifier,)
            ) as cursor:
                return dict(await cursor.fetchone())

        except Exception as e:
            logger.error(f"FAILED to update context for {identifier}: {e}")
            return None

    # ------------------------------------------------------------------
    # Statistics & Automation
    # ------------------------------------------------------------------

    async def get_booking_stats(self) -> Dict[str, Any]:
        """Return aggregate booking statistics asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute("SELECT status FROM bookings") as cursor:
            rows = await cursor.fetchall()

        stats: Dict[str, int] = {}
        for row in rows:
            status = row["status"] or "unknown"
            stats[status] = stats.get(status, 0) + 1
        return {"total": len(rows), "by_status": stats}

    async def get_pending_reminders(self, from_time: datetime) -> List[Dict[str, Any]]:
        """Fetch upcoming confirmed/rescheduled bookings needing reminders asynchronously."""
        db_manager = get_db()
        conn = await db_manager.get_connection()
        async with conn.execute(
            """
            SELECT * FROM bookings 
            WHERE start_time > ? 
            AND status IN ('confirmed', 'rescheduled')
            AND (reminder_24h_sent = 0 OR reminder_1h_sent = 0)
            """,
            (from_time.isoformat(),),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_reminder_sent(self, booking_id: str, label: str) -> None:
        """Update the database to flip the reminder flag asynchronously."""
        column_name = "reminder_24h_sent" if label == "24h" else "reminder_1h_sent"
        try:
            db_manager = get_db()
            conn = await db_manager.get_connection()
            await conn.execute(
                f"UPDATE bookings SET {column_name} = 1 WHERE id = ?", (booking_id,)
            )
            await conn.commit()
            logger.info(f"Marked {label} reminder as sent for booking {booking_id}")
        except Exception as e:
            logger.error(f"Error updating reminder status for {booking_id}: {e}")

    # ------------------------------------------------------------------
    # Token Credentials & Utilities
    # ------------------------------------------------------------------

    async def save_refresh_token(self, consultant_id: str, refresh_token: str) -> None:
        """Guarda o actualiza el token usando la conexión compartida del Singleton."""
        db_manager = get_db()
        conn = await db_manager.get_connection()

        # Opcional: Si mantienes cifrado de token activo, quita el comentario:
        refresh_token = self.cipher.encrypt(refresh_token.encode()).decode()

        await conn.execute(
            """
            INSERT INTO consultants (id, google_refresh_token, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                google_refresh_token = excluded.google_refresh_token,
                updated_at = CURRENT_TIMESTAMP
            """,
            (consultant_id, refresh_token),
        )
        await conn.commit()
        logger.info(f"Successfully committed refresh token update for {consultant_id}")

    async def get_decrypted_token(self, consultant_id: str) -> Optional[str]:
        """Fetch and decrypt Google OAuth refresh tokens asynchronously."""
        try:
            db_manager = get_db()
            conn = await db_manager.get_connection()
            async with conn.execute(
                "SELECT google_refresh_token FROM consultants WHERE id = ?",
                (consultant_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or not row["google_refresh_token"]:
                return None

            token = row["google_refresh_token"]
            # Opcional: Descomentar si usas la lógica de descifrado simétrico:
            token = self.cipher.decrypt(token.encode()).decode()
            return token
        except Exception as e:
            logger.error(f"Failed to retrieve token for {consultant_id}: {e}")
            raise e

    async def find_consultant_by_name(
        self, name_query: str
    ) -> Optional[Dict[str, Any]]:
        """Search for a consultant by name using partial matching asynchronously."""
        try:
            db_manager = get_db()
            conn = await db_manager.get_connection()
            async with conn.execute(
                "SELECT * FROM consultants WHERE name LIKE ?", (f"%{name_query}%",)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                logger.info(f"No consultant found matching: {name_query}")
                return None

            return dict(row)
        except Exception as e:
            logger.error(f"Error searching for consultant: {e}")
            return None

    async def find_consultants_by_name(self, name_query: str) -> List[Dict[str, Any]]:
        """Search for ALL consultants matching a name query asynchronously."""
        try:
            db_manager = get_db()
            conn = await db_manager.get_connection()

            async with conn.execute(
                "SELECT id, name, email, services, bio FROM consultants WHERE name LIKE ?",
                (f"%{name_query}%",),
            ) as cursor:
                rows = await cursor.fetchall()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching for consultants: {e}")
            return []

    async def find_consultant_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Search for a consultant by their exact email address asynchronously."""
        try:
            # Normalize email input to avoid casing issues
            clean_email = email.strip().lower()

            db_manager = get_db()
            conn = await db_manager.get_connection()

            # Using exact match '=' since email is a UNIQUE field in your schema
            async with conn.execute(
                "SELECT * FROM consultants WHERE email = ?", (clean_email,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                logger.info(f"No consultant found with email: {clean_email}")
                return None

            return dict(row)
        except Exception as e:
            logger.error(f"Error searching for consultant by email: {e}")
            return None
