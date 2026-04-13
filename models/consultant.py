"""Pydantic data models for the AI Booking application."""

from datetime import datetime, time
from enum import Enum
from typing import List, Optional
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import (
    BaseModel,
    EmailStr,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class DayOfWeek(str, Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"


# ---------------------------------------------------------------------------
# Availability models
# ---------------------------------------------------------------------------
class AvailabilityBase(BaseModel):
    day_of_week: DayOfWeek
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def check_time_range(self) -> "AvailabilityBase":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class AvailabilityCreate(AvailabilityBase):
    consultant_id: UUID


class AvailabilityUpdate(BaseModel):
    # We don't inherit from Base here because everything must be Optional
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    @model_validator(mode="after")
    def check_time_range(self) -> "AvailabilityUpdate":
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValueError("start_time must be before end_time")
        return self


class Availability(AvailabilityBase):
    """The full database record."""

    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Consultant models
# ---------------------------------------------------------------------------
class ConsultantBase(BaseModel):
    """Shared fields for all Consultant models."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    calendar_id: Optional[str] = None
    rate: Optional[float] = Field(None, ge=0)
    services: Optional[List[str]] = None
    bio: Optional[str] = Field(None, max_length=500)
    google_refresh_token: Optional[str] = Field(None, max_length=500)
    timezone: str = Field(
        default="UTC", description="IANA timezone string (e.g., 'Europe/London')"
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in available_timezones():
            raise ValueError(f"'{v}' is not a valid IANA timezone string")
        return v


class ConsultantCreate(ConsultantBase):
    """Used for POST /consultants. Mandatory fields here."""

    name: str
    email: EmailStr
    # We require at least one service at creation
    services: List[str] = Field(..., min_length=1)


class ConsultantUpdate(ConsultantBase):
    """Used for PATCH /consultants. Everything stays optional."""

    pass


class Consultant(ConsultantBase):
    """The full database record."""

    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
