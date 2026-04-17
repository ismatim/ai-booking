import pytest

from services.supabase_service import SupabaseService
from services.calendar_service import CalendarService

from utils.timezone import get_google_time_range
from config import get_settings

from utils.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()


def test_real_consultant_calendar_access():
    db = SupabaseService()
    calendar_service = CalendarService()

    # ASSIGN:
    # Get Consultant ID from integration environment
    #  Get the token we just saved via the browser flow
    test_id = settings.integration_test_consultant_id
    consultant = db.get_consultant_by_id(test_id)

    logger.info(f"Consultant {test_id} fields: {consultant}")
    encrypted_refresh_token = consultant.get("google_refresh_token")

    assert encrypted_refresh_token is not None, "Refresh token was not saved to DB!"

    service = calendar_service.get_auth_service(encrypted_refresh_token)

    logger.info(f"📅 Fetching events for consultant: {test_id}")

    # Define a time range (Now to 1 week from now)
    # Google API expects RFC3339 strings.
    time_min, time_max = get_google_time_range()

    # ACT:
    # Query the 'primary' calendar
    # Because we used OAuth, 'primary' automatically refers to the consultant's email
    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        # ASSERT
        assert isinstance(events, list), "Should return a list of events"

        if not events:
            logger.info("✅ Success: Connection works, but the calendar is empty.")
        else:
            logger.info(f"✅ Success: Found {len(events)} events!")
            for event in events:
                logger.info(
                    f" - Event: {event.get('summary')} at {event['start'].get('dateTime')}"
                )
                logger.info(f"{event}")

    except Exception as e:
        pytest.fail(f"❌ Failed to reach Google Calendar: {e}")


if __name__ == "__main__":
    # and it will trigger pytest on itself.
    pytest.main([__file__, "-s"])
