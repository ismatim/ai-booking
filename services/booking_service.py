"""Booking business logic orchestrating Calendar, Supabase, and WhatsApp."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from models import BookingCreate, BookingStatus, BookingUpdate
from services.calendar_service import CalendarService
from utils.helpers import build_slots_message, slot_to_str, parse_time_string
from utils.logger import get_logger
from services.database_service import DatabaseService

from config import get_settings

settings = get_settings()

logger = get_logger(__name__)


class BookingService:
    """Orchestrates availability checks, booking creation, and management."""

    def __init__(self) -> None:
        self.db = DatabaseService()
        self.calendar = CalendarService()

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    async def get_available_slots(
        self,
        date: datetime,
        consultant_id: Optional[str] = None,
        slot_duration_minutes: int = 60,
    ) -> List[Dict[str, Any]]:
        """Return available booking slots for a date.

        Queries Google Calendar for each matching consultant and returns
        free slots enriched with consultant details.

        Args:
            date: Target date.
            consultant_id: Restrict to a specific consultant UUID (optional).
            slot_duration_minutes: Duration of each slot in minutes.

        Returns:
            List of slot dicts with consultant info and ISO8601 times.
        """
        logger.info(
            "Checking availability for date %s with consultant_id=%s",
            date.date(),
            consultant_id,
        )
        if consultant_id:
            consultant = await self.db.get_consultant(consultant_id)

            logger.info(
                f"Consultant found: id={consultant.get('id')}, "
                f"name={consultant.get('name')}, "
                f"email={consultant.get('email')}, "
                f"calendar_id={consultant.get('calendar_id')}"
            )
            consultants = [consultant] if consultant else []
        else:
            # Fallback only if no ID is present (e.g., general availability check)
            consultants = await self.db.get_all_consultants()

        if not consultants:
            return []

        slots: List[Dict[str, Any]] = []

        for consultant in consultants[:5]:
            cal_id = consultant.get("calendar_id")
            availability = await self.db.get_availability_for_day(
                consultant_id=str(consultant["id"])
            )

            if not availability:
                logger.warning(
                    f"Skipping {consultant['name']}: No availability found for weekday {date.weekday()}"
                )
                continue

            logger.info(
                "Checking availability for consultant %s (Calendar ID: %s)",
                consultant["name"],
                cal_id,
            )
            if not cal_id:
                continue
            try:
                work_start = parse_time_string(availability["start_time"])
                work_end = parse_time_string(availability["end_time"])
                free = self.calendar.get_free_slots(
                    consultant_id=cal_id,
                    date_to_check=date,  # Correct keyword name
                    work_start=work_start,  # Required: e.g., "09:00:00"
                    work_end=work_end,  # Required: e.g., "17:00:00"
                    slot_duration_minutes=slot_duration_minutes,
                )
                for slot in free:
                    logger.info(
                        "Found free slot for %s: %s to %s",
                        consultant["name"],
                        slot["start"],
                        slot["end"],
                    )
                    slots.append(
                        {
                            "consultant_id": str(consultant["id"]),
                            "consultant_name": consultant["name"],
                            "rate": consultant.get("rate"),
                            "start_time": slot["start"],
                            "end_time": slot["end"],
                        }
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to fetch slots for consultant %s: %s",
                    consultant.get("name"),
                    exc,
                )

        # Sort by start time across all consultants
        slots.sort(key=lambda s: s["start_time"])
        return slots

    def format_slots_for_whatsapp(self, slots: List[Dict[str, Any]]) -> str:
        """Return a WhatsApp-formatted string listing available slots.

        Args:
            slots: Slot list from get_available_slots().

        Returns:
            Human-readable slot list string.
        """
        return build_slots_message(slots)

    # ------------------------------------------------------------------
    # Booking lifecycle
    # ------------------------------------------------------------------

    async def create_booking(
        self,
        user_phone_number: str,
        consultant_id: str,
        start_time: datetime,
        end_time: datetime,
        service: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a booking, add a Google Calendar event, and return booking data.

        Args:
            user_phone_number: User WhatsApp phone number string.
            consultant_id: Consultant UUID string.
            start_time: Booking start (UTC).
            end_time: Booking end (UTC).
            service: Optional service name.
            notes: Optional booking notes.

        Returns:
            Created booking dict.

        Raises:
            ValueError: If the user or consultant is not found.
        """
        user = await self.db.get_user_by_phone(user_phone_number)
        consultant = await self.db.get_consultant_by_id(consultant_id)

        if not user:
            raise ValueError(f"User with phone number {user_phone_number} not found")
        if not consultant:
            raise ValueError(f"Consultant {consultant_id} not found")

        target_tz = consultant.get("timezone") or settings.default_timezone

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=ZoneInfo(target_tz)).astimezone(
                ZoneInfo("UTC")
            )
        else:
            start_time = start_time.astimezone(ZoneInfo("UTC"))

        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=ZoneInfo(target_tz)).astimezone(
                ZoneInfo("UTC")
            )
        else:
            end_time = end_time.astimezone(ZoneInfo("UTC"))

        real_user_id = str(user["id"])

        booking_data = BookingCreate(
            user_id=UUID(real_user_id),
            consultant_id=UUID(consultant_id),
            start_time=start_time,  # Se envía en UTC puro
            end_time=end_time,  # Se envía en UTC puro
            notes=notes,
            service=service,
        )
        # Save the record in UTC
        booking = await self.db.create_booking(booking_data)

        cal_id = consultant.get("calendar_id")
        if cal_id:
            user_name = user.get("name") or user.get("phone_number", "Customer")
            summary = f"Booking: {user_name}"
            if service:
                summary += f" – {service}"
            description = f"Phone: {user.get('phone_number', 'N/A')}"
            if notes:
                description += f"\nNotes: {notes}"
            attendee_emails = (
                [consultant.get("email")] if consultant.get("email") else None
            )

            target_tz = consultant.get("timezone") or settings.default_timezone

            event_response = self.calendar.create_calendar_event(
                refresh_token=consultant.get("google_refresh_token"),
                summary=summary,
                start_time=start_time,  # UTC
                end_time=end_time,  # UTC
                consultant_email=attendee_emails,
                time_zone=target_tz,
            )

            if event_response and isinstance(event_response, dict):
                event_id = event_response.get("id")
                if event_id:
                    await self.db.set_calendar_event_id(str(booking["id"]), event_id)
                    booking["calendar_event_id"] = event_id

        return booking

    def cancel_booking(
        self, booking_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a booking and remove the Google Calendar event.

        Args:
            booking_id: Booking UUID string.
            user_id: Optional user UUID to verify ownership.

        Returns:
            Updated booking dict.

        Raises:
            ValueError: If booking not found or user mismatch.
        """
        booking = self.db.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")
        if user_id and str(booking["user_id"]) != user_id:
            raise ValueError("You are not authorised to cancel this booking")

        if booking.get("status") == BookingStatus.CANCELLED.value:
            raise ValueError("Booking is already cancelled")

        # Remove calendar event
        cal_event_id = booking.get("calendar_event_id")
        if cal_event_id:
            consultant = self.db.get_consultant_by_id(str(booking["consultant_id"]))
            if consultant and consultant.get("calendar_id"):
                self.calendar.delete_event(consultant["calendar_id"], cal_event_id)

        updated = self.db.cancel_booking(booking_id)
        logger.info("Cancelled booking %s", booking_id)
        return updated

    def reschedule_booking(
        self,
        booking_id: str,
        new_start_time: datetime,
        new_end_time: datetime,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reschedule a booking to a new time slot.

        Args:
            booking_id: Booking UUID string.
            new_start_time: New start time (UTC).
            new_end_time: New end time (UTC).
            user_id: Optional user UUID to verify ownership.

        Returns:
            Updated booking dict.

        Raises:
            ValueError: If booking not found or user mismatch.
        """
        booking = self.db.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")
        if user_id and str(booking["user_id"]) != user_id:
            raise ValueError("You are not authorised to reschedule this booking")

        update_data = BookingUpdate(
            start_time=new_start_time,
            end_time=new_end_time,
            status=BookingStatus.RESCHEDULED,
        )
        updated = self.db.update_booking(booking_id, update_data)

        # Update calendar event
        cal_event_id = booking.get("calendar_event_id")
        if cal_event_id:
            consultant = self.db.get_consultant_by_id(str(booking["consultant_id"]))
            if consultant and consultant.get("calendar_id"):
                self.calendar.update_event(
                    calendar_id=consultant["calendar_id"],
                    event_id=cal_event_id,
                    start_time=new_start_time,
                    end_time=new_end_time,
                )

        logger.info("Rescheduled booking %s to %s", booking_id, new_start_time)
        return updated

    def get_user_bookings_summary(self, user_id: str) -> str:
        """Return a WhatsApp-formatted summary of a user's upcoming bookings.

        Args:
            user_id: User UUID string.

        Returns:
            Formatted string for WhatsApp display.
        """
        bookings = self.db.get_bookings_by_user(user_id)
        active = [
            b
            for b in bookings
            if b.get("status")
            in (BookingStatus.CONFIRMED.value, BookingStatus.RESCHEDULED.value)
        ]
        if not active:
            return "📭 You have no upcoming bookings."

        lines = [f"📅 *Your upcoming bookings ({len(active)}):*\n"]
        for booking in active[:5]:
            start = datetime.fromisoformat(booking["start_time"])
            consultant = self.db.get_consultant_by_id(str(booking["consultant_id"]))
            consultant_name = consultant["name"] if consultant else "Unknown"
            service = booking.get("service", "Consultation")
            lines.append(
                f"• {slot_to_str(start, datetime.fromisoformat(booking['end_time']))}\n"
                f"  With: {consultant_name} | {service}\n"
                f"  Status: {booking['status'].capitalize()}\n"
                f"  ID: `{str(booking['id'])[:8]}...`"
            )
        return "\n".join(lines)

    def build_booking_confirmation(self, booking: Dict[str, Any]) -> str:
        """Build a WhatsApp confirmation message for a booking.

        Args:
            booking: Booking dict from Supabase.

        Returns:
            Formatted confirmation string.
        """
        start = datetime.fromisoformat(booking["start_time"])
        end = datetime.fromisoformat(booking["end_time"])
        consultant = self.db.get_consultant_by_id(str(booking["consultant_id"]))
        consultant_name = consultant["name"] if consultant else "Your consultant"

        lines = [
            "✅ *Booking Confirmed!*\n",
            f"📅 {slot_to_str(start, end)}",
            f"👤 With: {consultant_name}",
        ]
        if booking.get("service"):
            lines.append(f"🔧 Service: {booking['service']}")
        if consultant and consultant.get("rate"):
            lines.append(f"💰 Rate: ${consultant['rate']:.2f}/hr")
        lines.append(f"\n📌 Booking ID: `{str(booking['id'])[:8]}...`")
        lines.append("\nYou'll receive a reminder 24h and 1h before your appointment.")
        lines.append(
            "Reply *CANCEL <booking_id>* to cancel or *RESCHEDULE <booking_id>* to reschedule."
        )
        return "\n".join(lines)
