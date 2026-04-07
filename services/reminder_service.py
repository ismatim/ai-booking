"""Appointment reminder scheduler using APScheduler."""

from datetime import datetime, timezone
from typing import Any, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from services.supabase_service import SupabaseService
from services.whatsapp_service import WhatsAppService
from utils.helpers import slot_to_str
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# How many minutes either side of the threshold to send a reminder
REMINDER_WINDOW_MINUTES = 10


class ReminderService:
    """Schedules and sends WhatsApp reminders for upcoming bookings."""

    def __init__(self) -> None:
        self.db = SupabaseService()
        self.whatsapp = WhatsAppService()
        self.scheduler = AsyncIOScheduler()
        self._sent_reminders: set = set()  # Track sent reminders to avoid duplicates

    def start(self) -> None:
        """Start the background reminder scheduler."""
        self.scheduler.add_job(
            self._check_and_send_reminders,
            trigger=IntervalTrigger(minutes=settings.reminder_check_interval_minutes),
            id="reminder_check",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()
        logger.info(
            "Reminder scheduler started (interval: %d min)",
            settings.reminder_check_interval_minutes,
        )

    def stop(self) -> None:
        """Stop the background scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Reminder scheduler stopped")

    async def _check_and_send_reminders(self) -> None:
        """Check upcoming bookings and send due reminders."""
        now = datetime.now(timezone.utc)
        upcoming = self.db.get_upcoming_bookings(from_time=now)
        for booking in upcoming:
            await self._process_booking_reminders(booking, now)

    async def _process_booking_reminders(
        self, booking: Dict[str, Any], now: datetime
    ) -> None:
        """Send 24h and 1h reminders for a single booking if due.

        Args:
            booking: Booking dict from Supabase.
            now: Current UTC time.
        """
        booking_id = str(booking["id"])
        start = datetime.fromisoformat(booking["start_time"])

        hours_until = (start - now).total_seconds() / 3600

        for threshold, label in [(24, "24h"), (1, "1h")]:
            reminder_key = f"{booking_id}_{label}"
            if reminder_key in self._sent_reminders:
                continue

            # Send if within REMINDER_WINDOW_MINUTES of the threshold
            window_min = threshold - REMINDER_WINDOW_MINUTES / 60
            window_max = threshold + REMINDER_WINDOW_MINUTES / 60
            if window_min <= hours_until <= window_max:
                await self._send_reminder(booking, label)
                self._sent_reminders.add(reminder_key)

    async def _send_reminder(self, booking: Dict[str, Any], label: str) -> None:
        """Send a WhatsApp reminder message.

        Args:
            booking: Booking dict.
            label: '24h' or '1h'.
        """
        user = self.db.get_user_by_id(str(booking["user_id"]))
        if not user:
            return

        consultant = self.db.get_consultant_by_id(str(booking["consultant_id"]))
        consultant_name = consultant["name"] if consultant else "your consultant"

        start = datetime.fromisoformat(booking["start_time"])
        end = datetime.fromisoformat(booking["end_time"])
        slot_str = slot_to_str(start, end)

        message = self._build_reminder_message(
            label=label,
            slot_str=slot_str,
            consultant_name=consultant_name,
            booking_id=str(booking["id"]),
            service=booking.get("service", "Consultation"),
        )

        phone = user["phone_number"]
        # Redact phone number in logs: show only last 4 digits
        phone_masked = "***" + phone[-4:] if len(phone) >= 4 else "***"
        try:
            await self.whatsapp.send_text_message(to=phone, body=message)
            logger.info(
                "Sent %s reminder for booking %s to %s",
                label,
                booking["id"],
                phone_masked,
            )
        except Exception as exc:
            logger.error(
                "Failed to send %s reminder for booking %s: %s",
                label,
                booking["id"],
                exc,
            )

    @staticmethod
    def _build_reminder_message(
        label: str,
        slot_str: str,
        consultant_name: str,
        booking_id: str,
        service: str,
    ) -> str:
        """Build the reminder text message.

        Args:
            label: '24h' or '1h'.
            slot_str: Human-readable slot string.
            consultant_name: Consultant display name.
            booking_id: Booking UUID string.
            service: Service name.

        Returns:
            Formatted WhatsApp message string.
        """
        if label == "24h":
            intro = "⏰ *Reminder: Your appointment is tomorrow!*"
        else:
            intro = "⏰ *Reminder: Your appointment is in 1 hour!*"

        short_id = booking_id[:8]
        return (
            f"{intro}\n\n"
            f"📅 {slot_str}\n"
            f"👤 With: {consultant_name}\n"
            f"🔧 Service: {service}\n\n"
            f"Need to reschedule? Reply *RESCHEDULE {short_id}*\n"
            f"Need to cancel? Reply *CANCEL {short_id}*"
        )
