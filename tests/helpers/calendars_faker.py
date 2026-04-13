import uuid
from datetime import datetime, timedelta
from utils.timezone import get_now_utc, format_google_datetime


def generate_mock_google_event(
    summary: str = "Meeting",
    start_dt: datetime = None,
    is_all_day: bool = False,
    is_workspace: bool = False,
    is_transparent: bool = False,
):
    """
    Generates a dictionary mimicking a Google Calendar API event.
    """
    event_id = uuid.uuid4().hex
    # Default start to now if not provided
    start_dt = start_dt or datetime.now()

    # 1. Determine the key once
    key = "date" if is_all_day else "dateTime"

    # 2. Handle the math (still needed)
    start_dt = start_dt or get_now_utc()
    end_dt = start_dt + (timedelta(days=1) if is_all_day else timedelta(hours=1))

    # 3. Use the helper for the values
    event_start = {key: format_google_datetime(start_dt, all_day=is_all_day)}
    event_end = {key: format_google_datetime(end_dt, all_day=is_all_day)}

    # 2. Base Event Structure
    event = {
        "kind": "calendar#event",
        "id": event_id,
        "status": "confirmed",
        "summary": summary,
        "start": event_start,
        "end": event_end,
        "transparency": "transparent" if is_transparent else "opaque",
        "visibility": "public",
        "creator": {"email": "consultant@example.com"},
        "organizer": {"email": "consultant@example.com"},
    }

    # 3. Add Workspace-specific flavors
    if is_workspace and summary == "Home":
        event.update(
            {
                "eventType": "workingLocation",
                "workingLocationProperties": {"type": "homeOffice", "homeOffice": {}},
            }
        )
    elif is_workspace:
        event["eventType"] = "default"

    return event
