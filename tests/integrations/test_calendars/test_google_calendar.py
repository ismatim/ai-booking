import pytest
from google.oauth2 import service_account
from googleapiclient.discovery import build

from services.supabase_service import SupabaseService
from services.calendar_service import CalendarService

from utils.timezone import get_google_time_range
from config import get_settings

from utils.logger import get_logger

logger = get_logger(__name__)


settings = get_settings()
# --- CONFIGURATION ---
SERVICE_ACCOUNT_FILE = settings.google_calendar_credentials
TARGET_CALENDAR_ID = settings.integration_target_calendar_id
SCOPES = [settings.integration_scopes]


def test_calendar_integration():
    logger.info(f"🚀 Starting test for: {TARGET_CALENDAR_ID}")

    # 1. Credentials setup
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("calendar", "v3", credentials=creds)

    # 2. Use your helper instead of utcnow()
    # now is a timezone-aware datetime object
    now, tonight = get_google_time_range(days=1)

    logger.info(f"🕒 Checking range: {now.isoformat()} TO {tonight.isoformat()}")

    try:
        events_result = (
            service.events()
            .list(
                calendarId=TARGET_CALENDAR_ID,
                timeMin=now.isoformat(),  # isoformat() handles the +00:00 perfectly
                timeMax=tonight.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        if not events:
            print("✅ Connection OK: No events found (Calendar is empty today).")
        else:
            print(f"✅ Success! Found {len(events)} events:")
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                print(f" - [{start}] {event.get('summary')}")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")


def test_real_consultant_calendar_access():
    db = SupabaseService()
    calendar_service = CalendarService()

    # 1. Pull the ID you used in your '/test-auth' route
    test_id = "42694d00-e6a0-4f17-99db-f15bd80b2f60"

    # 2. Get the token we just saved via the browser flow
    consultant = db.get_consultant_by_id(test_id)

    logger.info(f"Consultant fields: {consultant}")
    # logger.info(f"Consultant fields: {consultant.__dict__}")
    encrypted_refresh_token = consultant.get("google_refresh_token")

    assert encrypted_refresh_token is not None, "Refresh token was not saved to DB!"

    service = calendar_service.get_auth_service(encrypted_refresh_token)

    logger.info(f"📅 Fetching events for consultant: {test_id}")

    # Define a time range (Now to 1 week from now)
    time_min, time_max = get_google_time_range()
    # Google API expects RFC3339 strings.

    try:
        # Query the 'primary' calendar
        # Because we used OAuth, 'primary' automatically refers to the consultant's email
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

        # 6. Assertions
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
