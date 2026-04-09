from fastapi import Depends, APIRouter
from utils.api import dev_only
from services import calendar_service

from utils.logger import get_logger

router = APIRouter(prefix="/tests", tags=["Tests", "Calendar"])

logger = get_logger(__name__)


@router.get("/calendar", dependencies=[Depends(dev_only)])
async def test_calendar(consultant_id: str):
    """
    Test if we can actually read the calendar using the stored token.
    """
    try:
        events = calendar_service.get_upcoming_events(consultant_id)

        if not events:
            return {"message": "Connection successful, but no upcoming events found."}

        # Clean up the output to just show titles and times
        simplified_events = [
            {"title": e.get("summary"), "start": e.get("start", {}).get("dateTime")}
            for e in events
        ]

        return {
            "status": "success",
            "consultant_id": consultant_id,
            "events_found": len(simplified_events),
            "next_events": simplified_events,
        }
    except Exception as e:
        logger.error(f"Calendar test failed: {e}")
        return {"status": "error", "message": str(e)}
