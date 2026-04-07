"""Pydantic data models for the AI Booking application."""

from models.availability import Availability, AvailabilityCreate, AvailabilityUpdate
from models.booking import Booking, BookingCreate, BookingUpdate
from models.consultant import Consultant, ConsultantCreate, ConsultantUpdate
from models.conversation import ConversationHistory, ConversationHistoryCreate, Message
from models.enums import BookingStatus, DayOfWeek
from models.responses import AvailableSlot, ErrorResponse, SuccessResponse
from models.user import User, UserCreate, UserUpdate
from models.whatsapp import (
    WhatsAppChange,
    WhatsAppContact,
    WhatsAppEntry,
    WhatsAppMessage,
    WhatsAppTextMessage,
    WhatsAppValue,
    WhatsAppWebhookPayload,
)

__all__ = [
    # enums
    "BookingStatus",
    "DayOfWeek",
    # user
    "UserCreate",
    "UserUpdate",
    "User",
    # consultant
    "ConsultantCreate",
    "ConsultantUpdate",
    "Consultant",
    # availability
    "AvailabilityCreate",
    "AvailabilityUpdate",
    "Availability",
    # booking
    "BookingCreate",
    "BookingUpdate",
    "Booking",
    # conversation
    "Message",
    "ConversationHistoryCreate",
    "ConversationHistory",
    # whatsapp
    "WhatsAppTextMessage",
    "WhatsAppMessage",
    "WhatsAppContact",
    "WhatsAppValue",
    "WhatsAppChange",
    "WhatsAppEntry",
    "WhatsAppWebhookPayload",
    # responses
    "SuccessResponse",
    "ErrorResponse",
    "AvailableSlot",
]
