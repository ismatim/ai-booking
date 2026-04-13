"""Pydantic data models for the AI Booking application."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    google_refresh_token: Optional[str] = Field(None, max_length=500)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
