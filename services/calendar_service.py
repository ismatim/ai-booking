"""Google Calendar integration for consultant availability."""

from datetime import datetime, time, timedelta
import json
import os
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_settings
from utils.logger import get_logger

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
        date_to_check: datetime,
        work_start: time,  # e.g., 09:00:00
        work_end: time,  # e.g., 17:00:00
        slot_duration_minutes: int = 60,
        time_zone: str = settings.default_timezone,
    ) -> List[Dict[str, Any]]:
        """Calculate and filter available time slots for a consultant by cross-checking Google Calendar busy intervals.

        Executes a targeted query against the external calendar service boundary, extracts occupied blocks,
        and runs standard interval overlapping analysis to yield localized, non-conflicting chunks.

        Args:
            consultant_id (str): Unique identification handle for the specific resource.
            date_to_check (datetime): Target day matrix for available window slicing.
            work_start (time): Daily working shift start boundary constraint.
            work_end (time): Daily working shift end boundary constraint.
            slot_duration_minutes (int, optional): Longevity factor for each individual interval slice. Defaults to 60.
            time_zone (str, optional): Target IANA timezone location identifier string.
                Defaults to "America/Argentina/Buenos_Aires".

        Returns:
            List[Dict[str, Any]]: Collection of empty appointment blocks containing ISO-8601 offset strings.

        Examples:
            >>> scheduler = BookingService()
            >>> check_day = datetime(2026, 4, 15, 0, 0)
            >>> open_slots = scheduler.get_free_slots(
            ...     consultant_id="c_9941",
            ...     date_to_check=check_day,
            ...     work_start=time(9, 0),
            ...     work_end=time(11, 0),
            ...     slot_duration_minutes=60
            ... )
            >>> print(open_slots)
            [{'start': '2026-04-15T09:00:00-03:00', 'end': '2026-04-15T10:00:00-03:00'}]
        """
        logger.info(
            f"Generating localized free slots ({time_zone}) for consultant {consultant_id} on {date_to_check.date()} with working hours {work_start} - {work_end}"
        )

        # Define the actual working window using the Consultant's specific Time Zone (not UTC)
        day_start = datetime.combine(
            date_to_check.date(), work_start, tzinfo=ZoneInfo(time_zone)
        )
        day_end = datetime.combine(
            date_to_check.date(), work_end, tzinfo=ZoneInfo(time_zone)
        )

        # Optimize thresholds for Google Calendar by providing ISO strings with explicit offsets (e.g., -03:00)
        time_min = day_start.isoformat()
        time_max = day_end.isoformat()

        try:
            service = self._get_service()
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,  # Google seamlessly resolves local offsets
                    timeMax=time_max,
                    maxResults=50,  # Increased capacity to guarantee tracking the complete daily workload block
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            busy_events = events_result.get("items", [])
        except Exception as exc:
            logger.error(f"Google API error for {consultant_id}: {exc}")
            return []

        # Construct Busy Intervals (Timezone-Aware)
        busy_intervals = []
        for event in busy_events:
            if event.get("transparency") == "transparent":
                logger.info(f"Skipping transparent event: {event.get('summary')}")
                continue

            start_raw = event["start"].get("dateTime") or event["start"].get("date")
            end_raw = event["end"].get("dateTime") or event["end"].get("date")

            if not start_raw or not end_raw:
                continue

            b_start = datetime.fromisoformat(start_raw)
            b_end = datetime.fromisoformat(end_raw)

            # If the event lacks a timezone (e.g., full-day events matching "date"),
            # assign the consultant's local timezone as a fallback to prevent misalignments.
            if b_start.tzinfo is None:
                b_start = b_start.replace(tzinfo=ZoneInfo(time_zone))
            if b_end.tzinfo is None:
                b_end = b_end.replace(tzinfo=ZoneInfo(time_zone))

            busy_intervals.append((b_start, b_end))

        # 4. Generate Available Time Slots
        free_slots = []
        current_slot_start = day_start
        slot_delta = timedelta(minutes=slot_duration_minutes)

        while current_slot_start + slot_delta <= day_end:
            current_slot_end = current_slot_start + slot_delta

            # Python natively evaluates cross-timezone evaluations as long as
            # both operational timestamps are timezone-aware.
            is_busy = any(
                current_slot_start < b_end and current_slot_end > b_start
                for b_start, b_end in busy_intervals
            )

            if not is_busy:
                free_slots.append(
                    {
                        # .isoformat() exports strings preserving structural local offset strings (e.g., 2026-06-12T09:00:00-03:00)
                        "start": current_slot_start.isoformat(),
                        "end": current_slot_end.isoformat(),
                    }
                )

            current_slot_start += slot_delta

        return free_slots

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------

    def create_calendar_event(
        self,
        refresh_token: str,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        consultant_email: list[str],
        time_zone: str = "America/Argentina/Buenos_Aires",
    ) -> dict:
        """
        Inserts a structured invitation event into the authenticated calendar,
        translating internal UTC datetimes into the target local timezone, and
        automatically generates an integrated Google Meet video link.

        Args:
            refresh_token: The OAuth2 refresh token utilized to authenticate the Google API client.
            summary: The title string of the calendar event (e.g., 'Booking: Juan Perez').
            start_time: A timezone-aware datetime object (ideally UTC) representing the event start.
            end_time: A timezone-aware datetime object (ideally UTC) representing the event end.
            consultant_email: A list containing the email addresses of the attendees to invite.
            time_zone: The IANA time zone identifier for the event display. Defaults to 'America/Argentina/Buenos_Aires'.

        Returns:
            A dictionary containing the full Event resource payload returned directly by the Google Calendar API.

        Input Example:
            >>> calendar_svc.create_calendar_event(
            ...     refresh_token="1//04G...",
            ...     summary="Booking: Alan Turing – Consultation",
            ...     start_time=datetime(2026, 6, 3, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
            ...     end_time=datetime(2026, 6, 3, 13, 0, 0, tzinfo=ZoneInfo("UTC")),
            ...     consultant_email=["alan.turing@itisminetzky.xyz"]
            ... )
        """
        # 'primary' refers to the calendar account context linked via OAuth
        calendar_id = "primary"
        service = self._get_auth_service(refresh_token)

        # If the objects does not have timezone then UTC is assigned.
        # If there is one, .astimezone() calculate the destination time.
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=ZoneInfo("UTC"))
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=ZoneInfo("UTC"))

        local_start = start_time.astimezone(ZoneInfo(time_zone))
        local_end = end_time.astimezone(ZoneInfo(time_zone))

        # Remove the 'Z' because Google uses timeZone parameter
        event_body = {
            "summary": summary,
            "start": {
                "dateTime": local_start.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": time_zone,
            },
            "end": {
                "dateTime": local_end.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": time_zone,
            },
            "attendees": [
                {
                    "email": email,
                    "responseStatus": "accepted",
                }
                for email in consultant_email
            ]
            if consultant_email
            else [],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"book-{int(start_time.timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        logger.info(
            f"Dispatching API event insert payload localized to {time_zone}: {event_body}"
        )

        return (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates="all",  # Forces immediate email notifications to attendees
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
