from datetime import datetime
from zoneinfo import ZoneInfo


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
