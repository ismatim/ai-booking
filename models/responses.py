"""Pydantic data models for the AI Booking application."""

from datetime import datetime, time, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------


class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


class AvailableSlot(BaseModel):
    consultant_id: UUID
    consultant_name: str
    start_time: datetime
    end_time: datetime
    service: Optional[str] = None
    rate: Optional[float] = None
