"""Google Calendar integration for consultant availability."""

import json
import os
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_settings
from utils.logger import get_logger
from zoneinfo import ZoneInfo


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
    # Availability helpers
    # ------------------------------------------------------------------
    def get_free_slots(
        self,
        consultant_id: str,
        date_to_check: datetime,  # Should be a UTC datetime at 00:00:00
        work_start: time,  # From Availability model
        work_end: time,  # From Availability model
        slot_duration_minutes: int = 60,
    ) -> List[Dict[str, Any]]:

        # 1. Define the Working Window in UTC
        # We combine the requested date with the consultant's working hours
        day_start = datetime.combine(
            date_to_check.date(), work_start, tzinfo=ZoneInfo("UTC")
        )
        day_end = datetime.combine(
            date_to_check.date(), work_end, tzinfo=ZoneInfo("UTC")
        )

        try:
            # Use the consultant-specific service we built earlier
            service = self._get_service_for_consultant(consultant_id)

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=day_start.isoformat(),  # isoformat() handles the 'Z' or '+00:00'
                    timeMax=day_end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            busy_events = events_result.get("items", [])
        except Exception as exc:
            logger.error(f"Google API error for {consultant_id}: {exc}")
            return []

        # 2. Build Busy Intervals (Keep them Timezone-Aware!)
        busy_intervals = []
        for event in busy_events:
            start_raw = event["start"].get("dateTime", event["start"].get("date"))
            end_raw = event["end"].get("dateTime", event["end"].get("date"))

            # fromisoformat handles 'Z' automatically in modern Python
            # If it's just a 'date' (all-day), we force it to UTC
            b_start = datetime.fromisoformat(start_raw)
            if b_start.tzinfo is None:
                b_start = b_start.replace(tzinfo=ZoneInfo("UTC"))

            b_end = datetime.fromisoformat(end_raw)
            if b_end.tzinfo is None:
                b_end = b_end.replace(tzinfo=ZoneInfo("UTC"))

            busy_intervals.append((b_start, b_end))

        # 3. Generate Slots
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

    def create_event(
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
            "start": {"dateTime": start_time.isoformat() + "Z", "timeZone": "UTC"},
            "end": {"dateTime": end_time.isoformat() + "Z", "timeZone": "UTC"},
        }
        if description:
            event["description"] = description
        if attendee_emails:
            event["attendees"] = [{"email": e} for e in attendee_emails]

        try:
            service = self._get_service()
            created = (
                service.events()
                .insert(calendarId=calendar_id, body=event, sendUpdates="all")
                .execute()
            )
            event_id: str = created["id"]
            logger.info("Created calendar event %s on %s", event_id, calendar_id)
            return event_id
        except HttpError as exc:
            logger.error("Failed to create calendar event: %s", exc)
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

    def get_busy_slots(
        self, calendar_id: str, start_time: datetime, end_time: datetime
    ):
        """
        Fetches 'busy' events from Google Calendar.
        """
        # In a real app, you'd use service.events().list(...)
        # For our simulation, let's see what events are actually there:
        return self.search_events(calendar_id, start_time, end_time)

    def get_available_slots(self, consultant_id: str, date_obj: datetime):
        """
        The 'Master' method:
        1. Gets DB hours
        2. Gets Google busy slots
        3. Generates free windows
        """
        # 1. Fetch Working Hours from DB
        day_name = date_obj.strftime("%A").lower()
        work_settings = self.db.get_availability_for_day(consultant_id, day_name)

        if not work_settings:
            logger.info(f"Consultant {consultant_id} is not working on {day_name}")
            return []

        # 2. Parse "09:00:00" into integers for your existing function
        # Split by ':' and take the first two parts (hour, minute)
        start_h, start_m = map(int, work_settings["start_time"].split(":")[:2])
        end_h, end_m = map(int, work_settings["end_time"].split(":")[:2])

        # 3. Call your refined slot generator
        return self.get_free_slots(
            calendar_id="primary",  # Or use consultant_id if stored as email
            consultant_id=consultant_id,  # Added so we can fetch the right token
            date=date_obj,
            business_start_hour=start_h,
            business_end_hour=end_h,
        )
