"""Booking CRUD API endpoints."""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from models import BookingCreate, BookingStatus, BookingUpdate
from services.booking_service import BookingService
from services.supabase_service import SupabaseService
from utils.logger import get_logger
from utils.validators import validate_booking_duration

logger = get_logger(__name__)

router = APIRouter(prefix="/bookings", tags=["Bookings"])

booking_svc = BookingService()
db_svc = SupabaseService()


@router.post("", summary="Create a new booking")
async def create_booking(data: BookingCreate) -> Dict[str, Any]:
    """Create a new booking for a user with a consultant."""
    if not validate_booking_duration(data.start_time, data.end_time):
        raise HTTPException(
            status_code=400, detail="Invalid booking duration (must be 15 min – 8 h)"
        )
    try:
        booking = booking_svc.create_booking(
            user_id=str(data.user_id),
            consultant_id=str(data.consultant_id),
            start_time=data.start_time,
            end_time=data.end_time,
            service=data.service,
            notes=data.notes,
        )
        return {"success": True, "data": booking}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Error creating booking: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", summary="List all bookings")
async def list_bookings(
    user_id: Optional[str] = Query(None, description="Filter by user UUID"),
    consultant_id: Optional[str] = Query(None, description="Filter by consultant UUID"),
    status: Optional[BookingStatus] = Query(None, description="Filter by status"),
) -> Dict[str, Any]:
    """Return bookings, optionally filtered by user, consultant, or status."""
    if user_id:
        bookings = db_svc.get_bookings_by_user(user_id)
    elif consultant_id:
        bookings = db_svc.get_bookings_by_consultant(consultant_id)
    else:
        bookings = db_svc.get_upcoming_bookings()

    if status:
        bookings = [b for b in bookings if b.get("status") == status.value]

    return {"success": True, "count": len(bookings), "data": bookings}


@router.get("/upcoming", summary="Get upcoming confirmed bookings")
async def get_upcoming_bookings() -> Dict[str, Any]:
    """Return all upcoming confirmed bookings."""
    bookings = db_svc.get_upcoming_bookings()
    return {"success": True, "count": len(bookings), "data": bookings}


@router.get("/{booking_id}", summary="Get booking by ID")
async def get_booking(booking_id: str) -> Dict[str, Any]:
    """Return a single booking by UUID."""
    booking = db_svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"success": True, "data": booking}


@router.put("/{booking_id}", summary="Update a booking")
async def update_booking(booking_id: str, data: BookingUpdate) -> Dict[str, Any]:
    """Update booking fields (start/end time, status, notes)."""
    booking = db_svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if data.start_time and data.end_time:
        if not validate_booking_duration(data.start_time, data.end_time):
            raise HTTPException(status_code=400, detail="Invalid booking duration")
    updated = db_svc.update_booking(booking_id, data)
    return {"success": True, "data": updated}


@router.post("/{booking_id}/cancel", summary="Cancel a booking")
async def cancel_booking(booking_id: str) -> Dict[str, Any]:
    """Cancel a booking and remove the associated calendar event."""
    try:
        updated = booking_svc.cancel_booking(booking_id)
        return {"success": True, "message": "Booking cancelled", "data": updated}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{booking_id}/reschedule", summary="Reschedule a booking")
async def reschedule_booking(
    booking_id: str,
    new_start_time: datetime,
    new_end_time: datetime,
) -> Dict[str, Any]:
    """Reschedule a booking to a new time slot."""
    if not validate_booking_duration(new_start_time, new_end_time):
        raise HTTPException(status_code=400, detail="Invalid booking duration")
    try:
        updated = booking_svc.reschedule_booking(
            booking_id=booking_id,
            new_start_time=new_start_time,
            new_end_time=new_end_time,
        )
        return {"success": True, "message": "Booking rescheduled", "data": updated}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
