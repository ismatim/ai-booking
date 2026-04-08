"""Pydantic data models for the AI Booking application."""

from datetime import datetime, time, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

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
