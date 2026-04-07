"""Input validation utilities for AI Booking application."""

import re
from datetime import datetime
from typing import Optional


def validate_phone_number(phone: str) -> bool:
    """Validate an E.164 formatted phone number.

    Args:
        phone: Phone number string (with or without leading '+').

    Returns:
        True if the number is valid E.164, False otherwise.
    """
    # E.164: optional '+', 7-15 digits
    pattern = r"^\+?[1-9]\d{6,14}$"
    return bool(re.match(pattern, phone.strip()))


def normalize_phone_number(phone: str) -> str:
    """Normalize a phone number to E.164 format (no leading +).

    Args:
        phone: Raw phone number string.

    Returns:
        Digits-only phone number string.
    """
    return re.sub(r"\D", "", phone)


def validate_datetime_range(start: datetime, end: datetime) -> bool:
    """Validate that start is strictly before end.

    Args:
        start: Start datetime.
        end: End datetime.

    Returns:
        True if start < end, False otherwise.
    """
    return start < end


def validate_booking_duration(
    start: datetime,
    end: datetime,
    min_minutes: int = 15,
    max_minutes: int = 480,
) -> bool:
    """Validate booking duration is within acceptable bounds.

    Args:
        start: Booking start datetime.
        end: Booking end datetime.
        min_minutes: Minimum booking duration in minutes (default 15).
        max_minutes: Maximum booking duration in minutes (default 480 = 8h).

    Returns:
        True if duration is within bounds, False otherwise.
    """
    if not validate_datetime_range(start, end):
        return False
    duration = (end - start).total_seconds() / 60
    return min_minutes <= duration <= max_minutes


def sanitize_text(text: Optional[str], max_length: int = 1000) -> Optional[str]:
    """Sanitize and truncate text input.

    Args:
        text: Input text to sanitize.
        max_length: Maximum allowed length (default 1000).

    Returns:
        Sanitized string or None if input is None/empty.
    """
    if not text:
        return None
    cleaned = text.strip()
    return cleaned[:max_length] if len(cleaned) > max_length else cleaned
