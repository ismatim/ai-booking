"""Pydantic data models for the AI Booking application."""

from datetime import datetime, time, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(from_attributes=True)
