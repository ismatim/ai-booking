"""Consultant Pydantic models for the AI Booking application."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


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
