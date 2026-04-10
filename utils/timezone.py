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
