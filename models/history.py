from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums for Data Integrity
# ---------------------------------------------------------------------------


class ChatType(str, Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


# ---------------------------------------------------------------------------
# Conversation Table Model
# ---------------------------------------------------------------------------


class Conversation(BaseModel):
    """Represents a row in the 'conversations' table."""

    id: UUID = Field(default_factory=uuid4)
    external_id: str  # The Twilio ConversationSid or Phone Number
    type: ChatType = ChatType.INDIVIDUAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Message Table Model
# ---------------------------------------------------------------------------


class Message(BaseModel):
    """Represents a single row in the 'messages' table."""

    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# "Joined" Models for Application Logic
# ---------------------------------------------------------------------------


class ConversationWithHistory(Conversation):
    """Used when fetching a conversation along with its messages."""

    messages: List[Message] = []
    context: Dict[str, Any] = {}
    conversation: Conversation
