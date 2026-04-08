"""Pydantic data models for the AI Booking application."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"


# ---------------------------------------------------------------------------
# Booking models
# ---------------------------------------------------------------------------


class BookingCreate(BaseModel):
    user_id: UUID
    consultant_id: UUID
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    service: Optional[str] = None


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[BookingStatus] = None
    notes: Optional[str] = None


class Booking(BaseModel):
    id: UUID
    user_id: UUID
    consultant_id: UUID
    start_time: datetime
    end_time: datetime
    status: BookingStatus
    notes: Optional[str] = None
    service: Optional[str] = None
    calendar_event_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    reminder_24h_sent: bool = False
    reminder_1h_sent: bool = False

    model_config = ConfigDict(from_attributes=True)
