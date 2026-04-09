"""Pydantic data models for the AI Booking application."""

from datetime import datetime, time
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict


class DayOfWeek(int, Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


# ---------------------------------------------------------------------------
# Availability models
# ---------------------------------------------------------------------------


class AvailabilityCreate(BaseModel):
    consultant_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time


class AvailabilityUpdate(BaseModel):
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class Availability(BaseModel):
    id: UUID
    consultant_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Consultant models
# ---------------------------------------------------------------------------


class ConsultantCreate(BaseModel):
    name: str
    email: EmailStr
    calendar_id: Optional[str] = None
    rate: Optional[float] = None
    services: Optional[List[str]] = None
    bio: Optional[str] = None


class ConsultantUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    calendar_id: Optional[str] = None
    rate: Optional[float] = None
    services: Optional[List[str]] = None
    bio: Optional[str] = None


class Consultant(BaseModel):
    id: UUID
    name: str
    email: str
    calendar_id: Optional[str] = None
    rate: Optional[float] = None
    services: Optional[List[str]] = None
    bio: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
