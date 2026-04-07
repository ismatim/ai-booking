"""Consultant management API endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from models import AvailabilityCreate, ConsultantCreate, ConsultantUpdate
from services.supabase_service import SupabaseService
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/consultants", tags=["Consultants"])

db_svc = SupabaseService()


@router.get("", summary="List all consultants")
async def list_consultants() -> Dict[str, Any]:
    """Return all consultant records."""
    consultants = db_svc.get_all_consultants()
    return {"success": True, "count": len(consultants), "data": consultants}


@router.post("", summary="Create a consultant")
async def create_consultant(data: ConsultantCreate) -> Dict[str, Any]:
    """Create a new consultant record."""
    consultant = db_svc.create_consultant(data)
    return {"success": True, "data": consultant}


@router.get("/{consultant_id}", summary="Get consultant by ID")
async def get_consultant(consultant_id: str) -> Dict[str, Any]:
    """Return a single consultant by UUID."""
    consultant = db_svc.get_consultant_by_id(consultant_id)
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    return {"success": True, "data": consultant}


@router.put("/{consultant_id}", summary="Update a consultant")
async def update_consultant(consultant_id: str, data: ConsultantUpdate) -> Dict[str, Any]:
    """Update consultant fields."""
    consultant = db_svc.get_consultant_by_id(consultant_id)
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    updated = db_svc.update_consultant(consultant_id, data)
    return {"success": True, "data": updated}


@router.delete("/{consultant_id}", summary="Delete a consultant")
async def delete_consultant(consultant_id: str) -> Dict[str, Any]:
    """Delete a consultant record."""
    consultant = db_svc.get_consultant_by_id(consultant_id)
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    db_svc.delete_consultant(consultant_id)
    return {"success": True, "message": "Consultant deleted"}


# ------------------------------------------------------------------
# Availability management
# ------------------------------------------------------------------


@router.get("/{consultant_id}/availability", summary="Get consultant availability")
async def get_availability(consultant_id: str) -> Dict[str, Any]:
    """Return weekly availability slots for a consultant."""
    availability = db_svc.get_availability(consultant_id=consultant_id)
    return {"success": True, "count": len(availability), "data": availability}


@router.post("/{consultant_id}/availability", summary="Set availability slot")
async def set_availability(consultant_id: str, data: AvailabilityCreate) -> Dict[str, Any]:
    """Upsert a weekly availability slot for a consultant."""
    if str(data.consultant_id) != consultant_id:
        raise HTTPException(
            status_code=400,
            detail="consultant_id in body does not match URL parameter",
        )
    slot = db_svc.set_availability(data)
    return {"success": True, "data": slot}


@router.delete("/availability/{availability_id}", summary="Delete availability slot")
async def delete_availability(availability_id: str) -> Dict[str, Any]:
    """Delete a specific availability slot."""
    db_svc.delete_availability(availability_id)
    return {"success": True, "message": "Availability slot deleted"}
