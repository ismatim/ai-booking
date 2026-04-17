"""Supabase database operations for AI Booking application."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from cryptography.fernet import Fernet
from config import get_settings

from supabase import Client, create_client

from models import (
    AvailabilityCreate,
    BookingCreate,
    BookingStatus,
    BookingUpdate,
    ConsultantCreate,
    ConsultantUpdate,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseService:
    """Provides CRUD operations for all Supabase tables."""

    def __init__(self) -> None:
        settings = get_settings()
        self.db: Client = create_client(settings.supabase_url, settings.supabase_key)
        settings = get_settings()
        # Initialize the cipher with your secret key
        self.cipher = Fernet(settings.encryption_key.encode())

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def get_or_create_user(
        self, phone_number: str, name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch an existing user by phone or create a new one.

        Args:
            phone_number: E.164 phone number (digits only).
            name: Optional display name.

        Returns:
            User record as dict.
        """
        result = (
            self.db.table("users")
            .select("*")
            .eq("phone_number", phone_number)
            .execute()
        )
        if result.data:
            return result.data[0]

        user_data: Dict[str, Any] = {"phone_number": phone_number}
        if name:
            user_data["name"] = name
        created = self.db.table("users").insert(user_data).execute()
        logger.info("Created new user (id will be assigned by DB)")
        return created.data[0]

    def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Fetch a user by phone number."""
        result = (
            self.db.table("users")
            .select("*")
            .eq("phone_number", phone_number)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a user by UUID."""
        result = self.db.table("users").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None

    def update_user(
        self, user_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update user fields."""
        result = self.db.table("users").update(data).eq("id", user_id).execute()
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Consultants
    # ------------------------------------------------------------------

    def get_all_consultants(self) -> List[Dict[str, Any]]:
        """Return all consultants."""
        result = self.db.table("consultants").select("*").execute()
        return result.data or []

    def get_consultant_by_id(self, consultant_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a consultant by UUID."""
        result = (
            self.db.table("consultants").select("*").eq("id", consultant_id).execute()
        )
        return result.data[0] if result.data else None

    def get_consultant(self, consultant_id: str) -> dict | None:
        """Fetches a single consultant by their UUID."""
        try:
            response = (
                self.db.table("consultants")
                .select("*")
                .eq("id", consultant_id)
                .maybe_single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error fetching consultant {consultant_id}: {e}")
            return None

    def create_consultant(self, data: ConsultantCreate) -> Dict[str, Any]:
        """Insert a new consultant record."""
        payload = data.model_dump(exclude_none=True)
        result = self.db.table("consultants").insert(payload).execute()
        logger.info("Created consultant: %s", data.name)
        return result.data[0]

    def update_consultant(
        self, consultant_id: str, data: ConsultantUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update consultant fields."""
        payload = data.model_dump(exclude_none=True)
        if not payload:
            return self.get_consultant_by_id(consultant_id)
        result = (
            self.db.table("consultants")
            .update(payload)
            .eq("id", consultant_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete_consultant(self, consultant_id: str) -> bool:
        """Delete a consultant by UUID."""
        self.db.table("consultants").delete().eq("id", consultant_id).execute()
        return True

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------
    def get_availability_for_day(self, consultant_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the working hours for a specific consultant and day.

        Args:
            consultant_id: UUID of the consultant.
            day_of_week: 'monday', 'tuesday', etc.
        """
        result = (
            self.db.table("availability")
            .select("start_time, end_time")
            .eq("consultant_id", consultant_id)
            .execute()
        )

        if result.data:
            # We return the first (and should be only) record
            # The times are strings like "09:00:00"
            return result.data[0]
        return None

    def set_availability(self, data: AvailabilityCreate) -> Dict[str, Any]:
        """Upsert an availability record (one per consultant + day)."""
        payload = {
            "consultant_id": str(data.consultant_id),
            "day_of_week": data.day_of_week.value,
            "start_time": data.start_time.isoformat(),
            "end_time": data.end_time.isoformat(),
        }
        result = (
            self.db.table("availability")
            .upsert(payload, on_conflict="consultant_id,day_of_week")
            .execute()
        )
        return result.data[0]

    def delete_availability(self, availability_id: str) -> bool:
        """Delete an availability slot by UUID."""
        self.db.table("availability").delete().eq("id", availability_id).execute()
        return True

    # ------------------------------------------------------------------
    # Bookings
    # ------------------------------------------------------------------

    def create_booking(self, data: BookingCreate) -> Dict[str, Any]:
        """Insert a new booking record."""
        payload = {
            "user_id": str(data.user_id),
            "consultant_id": str(data.consultant_id),
            "start_time": data.start_time.isoformat(),
            "end_time": data.end_time.isoformat(),
            "status": BookingStatus.CONFIRMED.value,
        }
        if data.notes:
            payload["notes"] = data.notes
        if data.service:
            payload["service"] = data.service
        result = self.db.table("bookings").insert(payload).execute()
        logger.info("Created booking for user %s", data.user_id)
        return result.data[0]

    def get_booking_by_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a booking by UUID."""
        result = self.db.table("bookings").select("*").eq("id", booking_id).execute()
        return result.data[0] if result.data else None

    def get_bookings_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all bookings for a given user."""
        result = (
            self.db.table("bookings")
            .select("*")
            .eq("user_id", user_id)
            .order("start_time", desc=True)
            .execute()
        )
        return result.data or []

    def get_bookings_by_consultant(self, consultant_id: str) -> List[Dict[str, Any]]:
        """Return all bookings for a given consultant."""
        result = (
            self.db.table("bookings")
            .select("*")
            .eq("consultant_id", consultant_id)
            .order("start_time", desc=True)
            .execute()
        )
        return result.data or []

    def get_upcoming_bookings(
        self, from_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Return confirmed bookings with start_time in the future."""
        if from_time is None:
            from_time = datetime.now(timezone.utc)
        result = (
            self.db.table("bookings")
            .select("*")
            .eq("status", BookingStatus.CONFIRMED.value)
            .gte("start_time", from_time.isoformat())
            .order("start_time")
            .execute()
        )
        return result.data or []

    def update_booking(
        self, booking_id: str, data: BookingUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update booking fields."""
        payload: Dict[str, Any] = {}
        if data.start_time:
            payload["start_time"] = data.start_time.isoformat()
        if data.end_time:
            payload["end_time"] = data.end_time.isoformat()
        if data.status:
            payload["status"] = data.status.value
        if data.notes is not None:
            payload["notes"] = data.notes
        if not payload:
            return self.get_booking_by_id(booking_id)
        result = (
            self.db.table("bookings").update(payload).eq("id", booking_id).execute()
        )
        return result.data[0] if result.data else None

    def cancel_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Mark a booking as cancelled."""
        result = (
            self.db.table("bookings")
            .update({"status": BookingStatus.CANCELLED.value})
            .eq("id", booking_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def set_calendar_event_id(self, booking_id: str, event_id: str) -> None:
        """Store the Google Calendar event ID on a booking."""
        self.db.table("bookings").update({"calendar_event_id": event_id}).eq(
            "id", booking_id
        ).execute()

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    def get_or_create_conversation(
        self, external_id: str, chat_type: str = "individual"
    ) -> Dict[str, Any]:
        """Finds or creates the conversation record and returns the row (including context)."""
        result = (
            self.db.table("conversations")
            .select("*")
            .eq("external_id", external_id)
            .execute()
        )

        if result.data:
            return result.data[0]

        # Create new conversation if it doesn't exist
        new_payload = {
            "external_id": external_id,
            "type": chat_type,
            "context": {},  # Initial empty context
        }
        res = self.db.table("conversations").insert(new_payload).execute()
        return res.data[0]

    def get_messages(
        self, conversation_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetches the latest messages for a specific conversation."""
        result = (
            self.db.table("messages")
            .select("role, content")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        # Reverse so Gemini gets them in chronological order
        return result.data[::-1]

    def save_message(self, conversation_id: str, role: str, content: str):
        """Inserts a single message row."""
        self.db.table("messages").insert(
            {"conversation_id": conversation_id, "role": role, "content": content}
        ).execute()

    def update_user_context(self, identifier: str, updates: dict):
        try:
            if not identifier:
                print("Error: No identifier (phone) provided to update_user_context")
                return None

            # 1. Fetch existing context safely
            query = (
                self.db.table("conversations")
                .select("context")
                .eq("external_id", identifier)
                .maybe_single()
            )
            res = query.execute()

            # 2. Check if res is None or has no data
            current_context = {}
            if res and hasattr(res, "data") and res.data:
                current_context = res.data.get("context", {})

            # 3. Merge updates
            new_context = {**current_context, **updates}

            # 4. Upsert (Update or Insert) the record
            return (
                self.db.table("conversations")
                .upsert(
                    {"external_id": identifier, "context": new_context},
                    on_conflict="external_id",
                )
                .execute()
            )

        except Exception as e:
            print(f"FAILED to update context for {identifier}: {e}")
            return None

    # ------------------------------------------------------------------
    # Statistics (admin)
    # ------------------------------------------------------------------

    def get_booking_stats(self) -> Dict[str, Any]:
        """Return aggregate booking statistics."""
        all_bookings = self.db.table("bookings").select("status").execute().data or []
        stats: Dict[str, int] = {}
        for row in all_bookings:
            status = row.get("status", "unknown")
            stats[status] = stats.get(status, 0) + 1
        return {"total": len(all_bookings), "by_status": stats}

    def get_pending_reminders(self, from_time: datetime) -> List[Dict[str, Any]]:
        """
        Fetch upcoming confirmed/rescheduled bookings that haven't
        had all reminders sent yet.
        """
        # We look for bookings starting in the future (up to ~25 hours from now)
        # and that are in a 'confirmed' or 'rescheduled' state.
        response = (
            self.db.table("bookings")
            .select("*")
            .gt("start_time", from_time.isoformat())
            .in_("status", ["confirmed", "rescheduled"])
            # Logic: Fetch if either of the reminders is still False
            .or_("reminder_24h_sent.eq.false,reminder_1h_sent.eq.false")
            .execute()
        )
        return response.data

    def mark_reminder_sent(self, booking_id: str, label: str) -> None:
        """
        Update the database to flip the reminder flag to True.

        Args:
            booking_id: The UUID of the booking.
            label: Either '24h' or '1h'.
        """
        column_name = "reminder_24h_sent" if label == "24h" else "reminder_1h_sent"

        try:
            self.db.table("bookings").update({column_name: True}).eq(
                "id", booking_id
            ).execute()

            logger.info(f"Marked {label} reminder as sent for booking {booking_id}")
        except Exception as e:
            logger.error(f"Error updating reminder status for {booking_id}: {e}")

    def save_refresh_token(self, consultant_id: str, refresh_token: str):
        """
        Securely saves the Google Refresh Token for a specific consultant.
        """
        try:
            # Encrypt the token
            encrypted_token = self.cipher.encrypt(refresh_token.encode()).decode()

            response = (
                self.db.table("consultants")
                .update({"google_refresh_token": encrypted_token})
                .eq("id", consultant_id)
                .execute()
            )

            if not response.data:
                logger.error(
                    f"❌ DATABASE UPDATE FAILED: No consultant found with ID {consultant_id}"
                )
                return False

        except Exception as e:
            print(f"❌ Failed to save refresh token: {e}")
            raise e

    def get_decrypted_token(self, consultant_id: str):
        # Fetch the encrypted string
        try:
            res = (
                self.db.table("consultants")
                .select("google_refresh_token")
                .eq("id", consultant_id)
                .single()
                .execute()
            )

            encrypted_token = res.data.get("google_refresh_token")
            if not encrypted_token:
                return None

            # Decrypt it back to plain text
            return self.cipher.decrypt(encrypted_token.encode()).decode()
        except Exception as e:
            print(f"❌ Failed to retrieve/decrypt token: {e}")
            raise e

    def find_consultant_by_name(self, name_query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a consultant by name using case-insensitive partial matching.
        """
        try:
            # We use .ilike for case-insensitive matching
            # The % wildcards allow 'Maria' to match 'Maria Jenkins'
            result = (
                self.db.table("consultants")
                .select("*")
                .ilike("name", f"%{name_query}%")
                .execute()
            )

            if not result.data:
                logger.info(f"No consultant found matching: {name_query}")
                return None

            # If there are multiple matches, we return the first one
            # Pro tip: You could later sort these by 'popularity' or 'relevance'
            return result.data[0]

        except Exception as e:
            logger.error(f"Error searching for consultant: {e}")
            return None
