"""Helper utilities for AI Booking application."""

from datetime import datetime, time
from typing import List, Optional
from zoneinfo import ZoneInfo

from config import get_settings

settings = get_settings()


def get_timezone() -> ZoneInfo:
    """Retrieve the configured IANA time zone for the application context.

    This acts as the single source of truth for time localization across the booking
    pipeline, relying on runtime system configuration.

    Returns:
        ZoneInfo: A time zone object corresponding to the configured application setting.

    Examples:
        >>> get_timezone()
        zoneinfo.ZoneInfo(key='America/New_York')
    """
    return ZoneInfo(settings.timezone)


def now_local() -> datetime:
    """Generate the current localized datetime.

    Captures the exact instantaneous system time and forces localization into the
    application's configured time zone.

    Returns:
        datetime: A timezone-aware datetime object representing the current moment.

    Examples:
        >>> now_local()
        datetime.datetime(2026, 5, 31, 9, 53, 0, tzinfo=zoneinfo.ZoneInfo(key='America/New_York'))
    """
    return datetime.now(tz=get_timezone())


def to_local(dt: datetime) -> datetime:
    """Convert a given datetime object to the configured application time zone.

    Safely processes both naive and aware datetimes. If the input datetime is naive,
    it is explicitly assumed to be in UTC before being converted to the local target zone.

    Args:
        dt (datetime): The datetime object to transform. Can be timezone-aware or naive.

    Returns:
        datetime: A timezone-aware datetime object shifted to the configured local zone.

    Examples:
        >>> naive_dt = datetime(2026, 4, 7, 14, 0)
        >>> to_local(naive_dt)
        datetime.datetime(2026, 4, 7, 10, 0, tzinfo=zoneinfo.ZoneInfo(key='America/New_York'))

        >>> utc_aware_dt = datetime(2026, 4, 7, 14, 0, tzinfo=ZoneInfo("UTC"))
        >>> to_local(utc_aware_dt)
        datetime.datetime(2026, 4, 7, 10, 0, tzinfo=zoneinfo.ZoneInfo(key='America/New_York'))
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(get_timezone())


def format_datetime(dt: datetime, fmt: str = "%A, %B %d %Y at %I:%M %p") -> str:
    """Convert a datetime instance into a localized, human-readable string.

    Ensures the target datetime is localized to the application's time zone
    prior to executing string formatting.

    Args:
        dt (datetime): The datetime instance to be processed.
        fmt (str, optional): The strftime-compatible layout design.
            Defaults to "%A, %B %d %Y at %I:%M %p" (e.g., Monday, April 07 2026 at 10:00 AM).

    Returns:
        str: A string representing the formatted, localized datetime.

    Examples:
        >>> utc_dt = datetime(2026, 4, 7, 14, 0, tzinfo=ZoneInfo("UTC"))
        >>> format_datetime(utc_dt)
        'Tuesday, April 07 2026 at 10:00 AM'

        >>> format_datetime(utc_dt, fmt="%Y-%m-%d %H:%M")
        '2026-04-07 10:00'
    """
    return to_local(dt).strftime(fmt)


def slot_to_str(start: datetime, end: datetime) -> str:
    """Format a distinct booking interval window into a human-friendly string.

    Converts both endpoints to local time and strips leading zeros from hour
    representations to deliver a clean user experience (e.g., '09:00 AM' becomes '9:00 AM').

    Args:
        start (datetime): The start boundary of the booking slot.
        end (datetime): The end boundary of the booking slot.

    Returns:
        str: A formatted span presentation,
            e.g., "Monday, April 07 2026 at 10:00 AM – 11:00 AM".

    Examples:
        >>> start_dt = datetime(2026, 4, 7, 13, 0, tzinfo=ZoneInfo("UTC"))
        >>> end_dt = datetime(2026, 4, 7, 14, 0, tzinfo=ZoneInfo("UTC"))
        >>> slot_to_str(start_dt, end_dt)
        'Tuesday, April 07 2026 at 9:00 AM – 10:00 AM'
    """
    start_local = to_local(start)
    end_local = to_local(end)
    date_part = start_local.strftime("%A, %B %d %Y")
    start_time = start_local.strftime("%I:%M %p").lstrip("0")
    end_time = end_local.strftime("%I:%M %p").lstrip("0")
    return f"{date_part} at {start_time} – {end_time}"


def build_slots_message(slots: List[dict], max_slots: int = 5) -> str:
    """Compile an explicit, numbered list of open booking windows for customer-facing interfaces.

    Processes incoming raw payloads (which may contain ISO-8601 strings or native datetime
    objects), bounds-checks the list against an explicit threshold, and formats output lines
    with standard WhatsApp markdown optimization.

    Args:
        slots (List[dict]): A collection of dictionaries representing available timeslots.
            Each dict should provide keys: 'start_time', 'end_time', and 'consultant_name'.
        max_slots (int, optional): The upper limit constraint for total returned slots to
            prevent mobile chat overflow. Defaults to 5.

    Returns:
        str: A fully localized, multi-line markdown message designed for conversational interaction.

    Examples:
        >>> active_slots = [
        ...     {
        ...         "start_time": "2026-04-07T14:00:00Z",
        ...         "end_time": "2026-04-07T15:00:00Z",
        ...         "consultant_name": "Alex Rivera"
        ...     }
        ... ]
        >>> print(build_slots_message(active_slots))
        📅 *Available slots:*
        <BLANKLINE>
        1. Tuesday, April 07 2026 at 10:00 AM – 11:00 AM with *Alex Rivera*
        <BLANKLINE>
        Reply with the number of your preferred slot to confirm booking.

        >>> build_slots_message([])
        '😔 No available slots found. Please try different dates.'
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
    """Validate and clean conversational text inputs to isolate a slot choice index.

    Sanitizes string inputs and checks boundaries to ensure user numerical responses match
    the list variants provided to them in previous conversation prompts.

    Args:
        text (str): Raw string slice received directly from a webhook or chat endpoint.
        max_slots (int): The absolute boundary limit of displayed slots available for validation.

    Returns:
        Optional[int]: A validated, 1-indexed integer selection if valid;
            otherwise returns None.

    Examples:
        >>> parse_slot_selection(" 3 \\n", max_slots=5)
        3
        >>> parse_slot_selection("6", max_slots=5)
        None
        >>> parse_slot_selection("invalid_choice", max_slots=5)
        None
    """
    stripped = text.strip()
    if stripped.isdigit():
        num = int(stripped)
        if 1 <= num <= max_slots:
            return num
    return None


def parse_time_string(time_str: str) -> time:
    """Safely parse an arbitrary time string into a native datetime.time object.

    Iterates systematically through common 12-hour AM/PM formats, 24-hour ISO structures,
    and secondary truncated variations to normalize mixed input origins.

    Args:
        time_str (str): The raw text layout representing a time structure.

    Returns:
        time: A completely valid datetime.time instance isolated from date constraints.

    Raises:
        ValueError: If the sanitized string sequence fails to correlate with any recognized
            internal layout pattern.

    Examples:
        >>> parse_time_string("09:00 AM")
        datetime.time(9, 0)
        >>> parse_time_string("05:00 PM")
        datetime.time(17, 0)
        >>> parse_time_string("14:30")
        datetime.time(14, 30)
        >>> parse_time_string("18:15:00")
        datetime.time(18, 15)
    """
    t_clean = time_str.strip()

    # Evaluate common layouts: 12h with AM/PM, 24h with seconds, 24h without seconds
    for fmt in ("%I:%M %p", "%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(t_clean, fmt).time()
        except ValueError:
            continue

    raise ValueError(
        f"Time data '{time_str}' does not match any known format layout configurations."
    )
