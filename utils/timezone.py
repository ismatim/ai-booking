from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from typing import Any, Dict, Optional


def to_utc(dt: datetime, local_tz_str: str) -> datetime:
    """Convert a local datetime to UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(local_tz_str))
    return dt.astimezone(ZoneInfo("UTC"))


def to_local(dt: datetime, local_tz_str: str) -> datetime:
    """Convert a UTC datetime to a consultant's local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo(local_tz_str))


def get_now_utc() -> datetime:
    """Get the current time in UTC, timezone-aware."""
    return datetime.now(ZoneInfo("UTC"))


# .isoformat() on a timezone-aware object handles the +00:00 perfectly.
def get_now_utc_iso():
    """
    Returns the current UTC time as an RFC3339 formatted string.
    Best for: Direct use in Google Calendar API parameters (timeMin/timeMax).
    """
    # Google requires the offset. .isoformat() on an aware object
    # produces exactly what Google needs: '2026-04-12T19:20:00+00:00'
    return get_now_utc().isoformat()


def get_google_time_range(days: int = 7):
    """
    Returns a tuple of (time_min, time_max) as ISO strings.
    Defaults to a 7-day range starting from now.
    """
    now = get_now_utc()
    future = now + timedelta(days=days)

    # Return both as strings ready for the Google API
    return now.isoformat(), future.isoformat()


def parse_google_datetime(time_dict: Dict[str, Any]) -> Optional[datetime]:
    """
    Parses Google's start/end time dictionaries into a UTC-aware datetime.
    Handles both 'dateTime' (specific time) and 'date' (all-day events).
    """
    if not time_dict:
        return None

    # Extract the raw string (check dateTime first, then date)
    raw = time_dict.get("dateTime") or time_dict.get("date")
    if not raw:
        return None

    # Parse the ISO string
    # Python 3.11+ handles 'Z' and offsets automatically
    dt = datetime.fromisoformat(raw)

    # Ensure it is timezone-aware and in UTC
    if dt.tzinfo is None:
        # If it was a 'date' (all-day), it's naive; force to UTC
        return dt.replace(tzinfo=timezone.utc)

    # If it had a different timezone, convert it to UTC
    return dt.astimezone(timezone.utc)


def format_readable_date(dt: datetime) -> str:
    """Example: Friday, April 10th"""
    # Using %d with a manual suffix if you want to be fancy
    return dt.strftime("%A, %B %d")


def format_readable_time(dt: datetime) -> str:
    """Example: 3:00 PM"""
    return dt.strftime("%I:%M %p").lstrip("0")


def format_full_session(start: datetime, end: datetime) -> str:
    """Example: Friday, April 10 @ 3:00 PM - 4:00 PM"""
    date_part = format_readable_date(start)
    start_time = format_readable_time(start)
    end_time = format_readable_time(end)
    return f"{date_part} @ {start_time} - {end_time}"
