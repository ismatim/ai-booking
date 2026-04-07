"""Admin operations API endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from services.supabase_service import SupabaseService
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

db_svc = SupabaseService()


@router.get("/stats", summary="Get booking statistics")
async def get_stats() -> Dict[str, Any]:
    """Return aggregate booking statistics."""
    stats = db_svc.get_booking_stats()
    return {"success": True, "data": stats}


@router.get("/users", summary="List all users")
async def list_users() -> Dict[str, Any]:
    """Return all registered users."""
    result = db_svc.db.table("users").select("*").execute()
    users = result.data or []
    return {"success": True, "count": len(users), "data": users}


@router.get("/users/{user_id}", summary="Get user by ID")
async def get_user(user_id: str) -> Dict[str, Any]:
    """Return a single user by UUID."""
    user = db_svc.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": user}


@router.delete("/users/{user_id}/conversation", summary="Clear user conversation history")
async def clear_conversation(user_id: str) -> Dict[str, Any]:
    """Clear the conversation history for a user."""
    user = db_svc.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db_svc.clear_conversation(user_id)
    return {"success": True, "message": "Conversation history cleared"}


@router.get("/bookings/all", summary="Get all bookings (admin)")
async def get_all_bookings() -> Dict[str, Any]:
    """Return all bookings regardless of status (admin view)."""
    result = db_svc.db.table("bookings").select("*").order("created_at", desc=True).execute()
    bookings = result.data or []
    return {"success": True, "count": len(bookings), "data": bookings}
