"""Google Calendar integration for consultant availability."""

import json
import os
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional
from cryptography.fernet import Fernet

from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_settings
from utils.logger import get_logger
from zoneinfo import ZoneInfo

from utils.timezone import get_google_time_range

settings = get_settings()
logger = get_logger(__name__)

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


class CalendarService:
    """Provides Google Calendar operations for availability and event management."""

    def __init__(self) -> None:
        self._service = None

        self.cipher = Fernet(settings.encryption_key.encode())

    def _get_service(self):
        """Lazily initialise and return the Google Calendar service client."""
        if self._service:
            return self._service

        creds_data = settings.google_calendar_credentials
        if not creds_data:
            raise ValueError(
                "GOOGLE_CALENDAR_CREDENTIALS environment variable is not set."
            )

        # Support both file path and raw JSON string
        if os.path.isfile(creds_data):
            with open(creds_data, "r") as f:
                creds_dict = json.load(f)
        else:
            creds_dict = json.loads(creds_data)

        if creds_dict.get("type") == "service_account":
            creds = ServiceCredentials.from_service_account_info(
                creds_dict, scopes=CALENDAR_SCOPES
            )
        else:
            creds = Credentials.from_authorized_user_info(creds_dict, CALENDAR_SCOPES)

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    # ------------------------------------------------------------------
    # Google Calendar Tokens helpers
    # ------------------------------------------------------------------
    def _get_auth_service(self, encrypted_token: str):
        """
        Builds a dedicated Google Calendar service for a specific consultant.
        Does NOT cache to self._service to avoid cross-user identity leaks.
        """
        try:
            # Decrypt the token
            refresh_token = self.cipher.decrypt(encrypted_token.encode()).decode()

            # Reconstruct credentials
            creds = Credentials(
                token=None,  # Automatically refreshed by the library
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_calendar_client_id,
                client_secret=settings.google_calendar_client_secret,
            )

            return build("calendar", "v3", credentials=creds)

        except Exception as e:
            logger.error(f"_get_auth_service: Failed to build Google service: {e}")
            raise

    # ------------------------------------------------------------------
    # Availability helpers
    # ------------------------------------------------------------------
    def get_free_slots(
        self,
        consultant_id: str,
        date_to_check: datetime,  # Should be a UTC datetime at 01:00:00
        work_start: time,  # From Availability model
        work_end: time,  # From Availability model
        slot_duration_minutes: int = 60,
    ) -> List[Dict[str, Any]]:

        logger.info(
            f"Generating free slots for consultant {consultant_id} on {date_to_check.date()} with working hours {work_start} - {work_end}"
        )
        # 2. Define the Working Window in UTC
        # We combine the requested date with the consultant's working hours
        day_start = datetime.combine(
            date_to_check.date(), work_start, tzinfo=ZoneInfo("UTC")
        )
        day_end = datetime.combine(
            date_to_check.date(), work_end, tzinfo=ZoneInfo("UTC")
        )

        # Use the consultant-specific service we built earlier
        time_min, time_max = get_google_time_range()
        try:
            service = self._get_service()
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
            busy_events = events_result.get("items", [])
        except Exception as exc:
            logger.error(f"Google API error for {consultant_id}: {exc}")
            return []

        # Build Busy Intervals (Keep them Timezone-Aware!)
        busy_intervals = []
        for event in busy_events:
            # If transparency is 'transparent', the user is "Free".
            # 'opaque' (or missing) means they are "Busy".
            if event.get("transparency") == "transparent":
                logger.info(f"Skipping transparent event: {event.get('summary')}")
                continue

            # --- IMPROVED: HANDLE DATE VS DATETIME ---
            start_raw = event["start"].get("dateTime") or event["start"].get("date")
            end_raw = event["end"].get("dateTime") or event["end"].get("date")

            if not start_raw or not end_raw:
                continue

            b_start = datetime.fromisoformat(start_raw)
            b_end = datetime.fromisoformat(end_raw)

            # Ensure UTC for comparison
            if b_start.tzinfo is None:
                b_start = b_start.replace(tzinfo=ZoneInfo("UTC"))
            if b_end.tzinfo is None:
                b_end = b_end.replace(tzinfo=ZoneInfo("UTC"))

            busy_intervals.append((b_start, b_end))

        # Generate Slots
        free_slots = []
        current_slot_start = day_start
        slot_delta = timedelta(minutes=slot_duration_minutes)

        while current_slot_start + slot_delta <= day_end:
            current_slot_end = current_slot_start + slot_delta

            # Check if this window hits any busy intervals
            is_busy = any(
                current_slot_start < b_end and current_slot_end > b_start
                for b_start, b_end in busy_intervals
            )

            if not is_busy:
                free_slots.append(
                    {
                        "start": current_slot_start.isoformat(),
                        "end": current_slot_end.isoformat(),
                    }
                )

            current_slot_start += slot_delta

        return free_slots

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------
    def create_event_invitation_event(
        self, refresh_token, summary, start_time, end_time, consultant_email
    ):
        # 'primary' now refers to the Service Account's own calendar
        # This will NEVER return a 404 because the bot owns this calendar
        calendar_id = "primary"
        service = self._get_auth_service(refresh_token)

        event_body = {
            "summary": summary,
            "start": {
                "dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "timeZone": "UTC",
            },
            "attendees": [
                {
                    "email": consultant_email,
                    "responseStatus": "accepted",
                },  # You can try to force-accept
            ],
            "conferenceData": {  # Optional: Adds a Google Meet link automatically
                "createRequest": {
                    "requestId": "sample123",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        logger.info(f"Creating event invitation: {event_body}")

        return (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates="all",  # This sends the email invites!
                conferenceDataVersion=1,
            )
            .execute()
        )

    def create_direct_event(
        self,
        calendar_id: str,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        attendee_emails: Optional[List[str] | None] = None,
    ) -> Optional[str]:
        """Create a Google Calendar event and return its event ID.

        Args:
            calendar_id: Target calendar ID.
            summary: Event title.
            start_time: Event start (UTC).
            end_time: Event end (UTC).
            description: Optional event description.
            attendee_emails: Optional list of attendee email addresses.

        Returns:
            Created event ID string, or None on failure.
        """
        event: Dict[str, Any] = {
            "summary": summary,
            "start": {
                "dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "timeZone": "UTC",
            },
        }
        if description:
            event["description"] = description
        if attendee_emails:
            event["attendees"] = [
                {"email": email} for email in attendee_emails if email
            ]

        logger.info(f"create_event: {event}")
        try:
            service = self._get_service()
            created = (
                service.events()
                .insert(calendarId=calendar_id, body=event, sendUpdates="all")
                .execute()
            )
            event_id: str = created["id"]
            logger.info(
                "create_event: Created calendar event %s on %s", event_id, calendar_id
            )
            return event_id
        except HttpError as exc:
            logger.error("create_event: Failed to create calendar event: %s", exc)
            return None

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        summary: Optional[str] = None,
    ) -> bool:
        """Update an existing calendar event.

        Args:
            calendar_id: Calendar containing the event.
            event_id: Google Calendar event ID.
            start_time: New start time (optional).
            end_time: New end time (optional).
            summary: New event title (optional).

        Returns:
            True on success, False on failure.
        """
        try:
            service = self._get_service()
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )
            if start_time:
                event["start"] = {
                    "dateTime": start_time.isoformat() + "Z",
                    "timeZone": "UTC",
                }
            if end_time:
                event["end"] = {
                    "dateTime": end_time.isoformat() + "Z",
                    "timeZone": "UTC",
                }
            if summary:
                event["summary"] = summary
            service.events().update(
                calendarId=calendar_id, eventId=event_id, body=event, sendUpdates="all"
            ).execute()
            return True
        except HttpError as exc:
            logger.error("Failed to update calendar event %s: %s", event_id, exc)
            return False

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete a calendar event.

        Args:
            calendar_id: Calendar containing the event.
            event_id: Google Calendar event ID.

        Returns:
            True on success, False on failure.
        """
        try:
            service = self._get_service()
            service.events().delete(
                calendarId=calendar_id, eventId=event_id, sendUpdates="all"
            ).execute()
            logger.info("Deleted calendar event %s", event_id)
            return True
        except HttpError as exc:
            logger.error("Failed to delete calendar event %s: %s", event_id, exc)
            return False
