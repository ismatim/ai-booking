import pytest
from datetime import datetime, time
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo
from services.calendar_service import CalendarService


@pytest.fixture
def calendar_service():
    """Fixture to initialize the service with mocked dependencies."""
    with (
        patch("services.calendar_service.get_settings"),
    ):
        service = CalendarService()
        return service


def test_get_free_slots_with_conflict(calendar_service):
    # --- SETUP ---
    # Day: April 10, 2026
    # Working Hours: 09:00 to 12:00 (3 hours total)
    test_date = datetime(2026, 4, 10, tzinfo=ZoneInfo("UTC"))
    work_start = time(9, 0)
    work_end = time(12, 0)

    # Mock Google Busy Event: 10:00 to 11:00
    mock_busy_event = {
        "items": [
            {
                "start": {"dateTime": "2026-04-10T10:00:00Z"},
                "end": {"dateTime": "2026-04-10T11:00:00Z"},
                "summary": "Busy Meeting",
            }
        ]
    }

    # Mock the internal _get_service_for_consultant to return a fake API client
    mock_google_api = MagicMock()
    mock_google_api.events().list().execute.return_value = mock_busy_event
    calendar_service._get_service_for_consultant = MagicMock(
        return_value=mock_google_api
    )

    # --- EXECUTE ---
    # We expect 60-minute slots.
    # 09:00-10:00 -> FREE
    # 10:00-11:00 -> BUSY (Should be missing)
    # 11:00-12:00 -> FREE
    slots = calendar_service.get_free_slots(
        consultant_id="fake-uuid",
        date_to_check=test_date,
        work_start=work_start,
        work_end=work_end,
        slot_duration_minutes=60,
    )

    # --- ASSERT ---
    assert len(slots) == 2
    assert slots[0]["start"] == "2026-04-10T09:00:00+00:00"
    assert slots[1]["start"] == "2026-04-10T11:00:00+00:00"

    # Ensure the 10:00 slot was skipped
    starts = [s["start"] for s in slots]
    assert "2026-04-10T10:00:00+00:00" not in starts
