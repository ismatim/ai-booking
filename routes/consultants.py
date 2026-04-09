"""Consultant management API endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from models import AvailabilityCreate, ConsultantCreate, ConsultantUpdate
from services.supabase_service import SupabaseService
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/consultants", tags=["Consultants"])

supabase_service = SupabaseService()


@router.get("", summary="List all consultants")
async def list_consultants() -> Dict[str, Any]:
    """Return all consultant records."""
    consultants = supabase_service.get_all_consultants()
    return {"success": True, "count": len(consultants), "data": consultants}


@router.post("", summary="Create a consultant")
async def create_consultant(data: ConsultantCreate) -> Dict[str, Any]:
    """Create a new consultant record."""
    try:
        consultant = supabase_service.create_consultant(data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error("Error creating consultant: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"success": True, "data": consultant}


@router.get("/{consultant_id}", summary="Get consultant by ID")
async def get_consultant(consultant_id: str) -> Dict[str, Any]:
    """Return a single consultant by UUID."""
    consultant = supabase_service.get_consultant_by_id(consultant_id)
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    return {"success": True, "data": consultant}


@router.put("/{consultant_id}", summary="Update a consultant")
async def update_consultant(
    consultant_id: str, data: ConsultantUpdate
) -> Dict[str, Any]:
    """Update consultant fields."""
    consultant = supabase_service.get_consultant_by_id(consultant_id)
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    updated = supabase_service.update_consultant(consultant_id, data)
    return {"success": True, "data": updated}


@router.delete("/{consultant_id}", summary="Delete a consultant")
async def delete_consultant(consultant_id: str) -> Dict[str, Any]:
    """Delete a consultant record."""
    consultant = supabase_service.get_consultant_by_id(consultant_id)
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    supabase_service.delete_consultant(consultant_id)
    return {"success": True, "message": "Consultant deleted"}


# ------------------------------------------------------------------
# Availability management
# ------------------------------------------------------------------


@router.get("/{consultant_id}/availability", summary="Get consultant availability")
async def get_availability(consultant_id: str) -> Dict[str, Any]:
    """Return weekly availability slots for a consultant."""
    availability = supabase_service.get_availability(consultant_id=consultant_id)
    return {"success": True, "count": len(availability), "data": availability}


@router.post("/{consultant_id}/availability", summary="Set availability slot")
async def set_availability(
    consultant_id: str, data: AvailabilityCreate
) -> Dict[str, Any]:
    """Upsert a weekly availability slot for a consultant."""
    if str(data.consultant_id) != consultant_id:
        raise HTTPException(
            status_code=400,
            detail="consultant_id in body does not match URL parameter",
        )
    slot = supabase_service.set_availability(data)
    return {"success": True, "data": slot}


@router.delete("/availability/{availability_id}", summary="Delete availability slot")
async def delete_availability(availability_id: str) -> Dict[str, Any]:
    """Delete a specific availability slot."""
    supabase_service.delete_availability(availability_id)
    return {"success": True, "message": "Availability slot deleted"}
