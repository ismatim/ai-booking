"""Helper utilities for AI Booking application."""

from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from config import get_settings

settings = get_settings()


def get_timezone() -> ZoneInfo:
    """Return the configured application timezone."""
    return ZoneInfo(settings.timezone)


def now_local() -> datetime:
    """Return the current datetime in the configured timezone."""
    return datetime.now(tz=get_timezone())


def to_local(dt: datetime) -> datetime:
    """Convert a UTC datetime to the configured local timezone.

    Args:
        dt: Datetime object (assumed UTC if naive).

    Returns:
        Timezone-aware datetime in the local timezone.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(get_timezone())


def format_datetime(dt: datetime, fmt: str = "%A, %B %d %Y at %I:%M %p") -> str:
    """Format a datetime for human-readable display.

    Args:
        dt: Datetime to format.
        fmt: strftime format string.

    Returns:
        Formatted datetime string.
    """
    return to_local(dt).strftime(fmt)


def slot_to_str(start: datetime, end: datetime) -> str:
    """Return a human-readable time-slot string.

    Args:
        start: Slot start time.
        end: Slot end time.

    Returns:
        Formatted slot string, e.g. "Monday, April 07 2026 at 10:00 AM – 11:00 AM".
    """
    start_local = to_local(start)
    end_local = to_local(end)
    date_part = start_local.strftime("%A, %B %d %Y")
    start_time = start_local.strftime("%I:%M %p").lstrip("0")
    end_time = end_local.strftime("%I:%M %p").lstrip("0")
    return f"{date_part} at {start_time} – {end_time}"


def build_slots_message(slots: List[dict], max_slots: int = 5) -> str:
    """Build a numbered WhatsApp message listing available slots.

    Args:
        slots: List of slot dicts with 'start_time', 'end_time', 'consultant_name'.
        max_slots: Maximum number of slots to display.

    Returns:
        Formatted string with numbered slot list.
    """
    if not slots:
        return "😔 No available slots found. Please try different dates."

    lines = ["📅 *Available slots:*\n"]
    for idx, slot in enumerate(slots[:max_slots], start=1):
        start = slot.get("start_time")
        end = slot.get("end_time")
        consultant = slot.get("consultant_name", "Consultant")
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        lines.append(f"{idx}. {slot_to_str(start, end)} with *{consultant}*")

    lines.append("\nReply with the number of your preferred slot to confirm booking.")
    return "\n".join(lines)


def parse_slot_selection(text: str, max_slots: int) -> Optional[int]:
    """Parse a user's slot selection from their message.

    Args:
        text: Raw user message text.
        max_slots: Total number of available slots (for bounds check).

    Returns:
        1-based slot index if valid, None otherwise.
    """
    stripped = text.strip()
    if stripped.isdigit():
        num = int(stripped)
        if 1 <= num <= max_slots:
            return num
    return None
