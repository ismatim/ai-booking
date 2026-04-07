"""Google Calendar integration for consultant availability."""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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

    def _get_service(self):
        """Lazily initialise and return the Google Calendar service client."""
        if self._service:
            return self._service

        creds_data = settings.google_calendar_credentials
        if not creds_data:
            raise ValueError("GOOGLE_CALENDAR_CREDENTIALS environment variable is not set.")

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
        calendar_id: str,
        date: datetime,
        slot_duration_minutes: int = 60,
        business_start_hour: int = 9,
        business_end_hour: int = 17,
    ) -> List[Dict[str, Any]]:
        """Return free time slots for a calendar on a given date.

        Args:
            calendar_id: Google Calendar ID to query.
            date: The date to check availability for.
            slot_duration_minutes: Duration of each slot in minutes.
            business_start_hour: Start of business hours (24h, default 9).
            business_end_hour: End of business hours (24h, default 17).

        Returns:
            List of dicts with 'start' and 'end' ISO8601 strings.
        """
        day_start = date.replace(
            hour=business_start_hour, minute=0, second=0, microsecond=0
        )
        day_end = date.replace(
            hour=business_end_hour, minute=0, second=0, microsecond=0
        )

        try:
            service = self._get_service()
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=day_start.isoformat() + "Z",
                    timeMax=day_end.isoformat() + "Z",
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            busy_events = events_result.get("items", [])
        except HttpError as exc:
            logger.error("Google Calendar API error: %s", exc)
            return []

        # Build busy intervals
        busy_intervals = []
        for event in busy_events:
            start_raw = event["start"].get("dateTime", event["start"].get("date"))
            end_raw = event["end"].get("dateTime", event["end"].get("date"))
            start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
            busy_intervals.append((start_dt.replace(tzinfo=None), end_dt.replace(tzinfo=None)))

        # Generate all possible slots and filter out busy ones
        free_slots = []
        slot_start = day_start
        slot_delta = timedelta(minutes=slot_duration_minutes)
        while slot_start + slot_delta <= day_end:
            slot_end = slot_start + slot_delta
            if not self._is_overlapping(slot_start, slot_end, busy_intervals):
                free_slots.append(
                    {
                        "start": slot_start.isoformat(),
                        "end": slot_end.isoformat(),
                    }
                )
            slot_start += slot_delta

        return free_slots

    def _is_overlapping(
        self,
        slot_start: datetime,
        slot_end: datetime,
        busy_intervals: List[tuple],
    ) -> bool:
        """Return True if the slot overlaps with any busy interval."""
        for busy_start, busy_end in busy_intervals:
            if slot_start < busy_end and slot_end > busy_start:
                return True
        return False

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
        attendee_emails: Optional[List[str]] = None,
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
            event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
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
