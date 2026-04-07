"""Availability Pydantic models for the AI Booking application."""

from datetime import datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from models.enums import DayOfWeek


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

    class Config:
        from_attributes = True
