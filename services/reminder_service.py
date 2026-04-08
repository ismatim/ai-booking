"""Appointment reminder scheduler using APScheduler via Twilio."""

from datetime import datetime, timezone
from typing import Any, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from services.supabase_service import SupabaseService
from services.meta_service import MetaService  # File remains
from services.twilio_service import TwilioService  # New primary
from utils.helpers import slot_to_str
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ReminderService:
    """Schedules and sends WhatsApp reminders. Currently using Twilio."""

    def __init__(self) -> None:
        self.db = SupabaseService()
        self.twilio = TwilioService()
        self.meta = MetaService()  # Kept in code, ready to use

        # --- SET THE PRIMARY MESSENGER HERE ---
        self.messenger = self.twilio

        self.scheduler = AsyncIOScheduler()

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
            f"Reminder scheduler started using Twilio (interval: {settings.reminder_check_interval_minutes} min)"
        )

    def stop(self) -> None:
        """Stop the background scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Reminder scheduler stopped")

    async def _check_and_send_reminders(self) -> None:
        """Check upcoming bookings and send due reminders."""
        now = datetime.now(timezone.utc)

        # RECOMMENDED: Fetch only confirmed bookings that still need reminders
        upcoming = self.db.get_pending_reminders(from_time=now)

        for booking in upcoming:
            await self._process_booking_reminders(booking, now)

    async def _process_booking_reminders(
        self, booking: Dict[str, Any], now: datetime
    ) -> None:
        """Logic to decide if a 24h or 1h reminder is due."""
        booking_id = str(booking["id"])
        start = datetime.fromisoformat(booking["start_time"])
        hours_until = (start - now).total_seconds() / 3600

        # 24-Hour Reminder Logic
        if 0 < hours_until <= 24 and not booking.get("reminder_24h_sent"):
            success = await self._send_reminder(booking, "24h")
            if success:
                self.db.mark_reminder_sent(booking_id, "24h")

        # 1-Hour Reminder Logic
        elif 0 < hours_until <= 1 and not booking.get("reminder_1h_sent"):
            success = await self._send_reminder(booking, "1h")
            if success:
                self.db.mark_reminder_sent(booking_id, "1h")

    async def _send_reminder(self, booking: Dict[str, Any], label: str) -> bool:
        """Executes the send via the primary messenger."""
        user = self.db.get_user_by_id(str(booking["user_id"]))
        if not user:
            return False

        consultant = self.db.get_consultant_by_id(str(booking["consultant_id"]))
        consultant_name = consultant["name"] if consultant else "your consultant"

        start = datetime.fromisoformat(booking["start_time"])
        end = datetime.fromisoformat(booking["end_time"])

        message = self._build_reminder_message(
            label=label,
            slot_str=slot_to_str(start, end),
            consultant_name=consultant_name,
            booking_id=str(booking["id"]),
            service=booking.get("service", "Consultation"),
        )

        try:
            # We use the 'messenger' variable which points to Twilio
            await self.messenger.send_text_message(
                to=user["phone_number"], body=message
            )
            logger.info(f"Sent {label} Twilio reminder for booking {booking['id']}")
            return True
        except Exception as exc:
            logger.error(f"Failed to send {label} Twilio reminder: {exc}")
            return False

    @staticmethod
    def _build_reminder_message(
        label, slot_str, consultant_name, booking_id, service
    ) -> str:
        intro = (
            "⏰ *Reminder: Appointment tomorrow!*"
            if label == "24h"
            else "⏰ *Reminder: Appointment in 1 hour!*"
        )
        short_id = booking_id[:8]
        return (
            f"{intro}\n\n"
            f"📅 {slot_str}\n"
            f"👤 With: {consultant_name}\n"
            f"🔧 Service: {service}\n\n"
            f"To reschedule: *RESCHEDULE {short_id}*\n"
            f"To cancel: *CANCEL {short_id}*"
        )
