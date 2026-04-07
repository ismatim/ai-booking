"""Pydantic data models for the AI Booking application."""

from datetime import datetime, time, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"


class DayOfWeek(int, Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


# ---------------------------------------------------------------------------
# User models
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    phone_number: str = Field(..., description="WhatsApp phone number in E.164 format")
    name: Optional[str] = None
    language: str = "en"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None


class User(BaseModel):
    id: UUID
    phone_number: str
    name: Optional[str] = None
    language: str = "en"
    created_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Conversation history models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationHistoryCreate(BaseModel):
    user_id: UUID
    messages: List[Message] = []
    context: Dict[str, Any] = {}


class ConversationHistory(BaseModel):
    id: UUID
    user_id: UUID
    messages: List[Message]
    context: Dict[str, Any]
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# WhatsApp webhook models
# ---------------------------------------------------------------------------


class WhatsAppTextMessage(BaseModel):
    body: str


class WhatsAppMessage(BaseModel):
    id: str
    from_: str = Field(alias="from")
    timestamp: str
    type: str
    text: Optional[WhatsAppTextMessage] = None

    class Config:
        populate_by_name = True


class WhatsAppContact(BaseModel):
    profile: Dict[str, Any]
    wa_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: Dict[str, Any]
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None
    statuses: Optional[List[Dict[str, Any]]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: List[WhatsAppEntry]


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
