"""
Unified access point for all Pydantic models.
This allows for 'from models import X' syntax.
"""

# 1. Enums & Shared Types
from .booking import BookingStatus
from .consultant import DayOfWeek

# 2. User Models
from .user import User, UserCreate, UserUpdate

# 3. Consultant & Availability Models
from .consultant import (
    Consultant,
    ConsultantCreate,
    ConsultantUpdate,
    Availability,
    AvailabilityCreate,
    AvailabilityUpdate,
)

# 4. Booking Models
from .booking import Booking, BookingCreate, BookingUpdate

# 5. Conversation & AI Models
# Note: Usually kept in an 'ai.py' or 'history.py' within models/
from .history import Message, ConversationHistory, ConversationHistoryCreate

# 6. Messaging / Webhook Models
from .whatsapp import (
    WhatsAppWebhookPayload,
    WhatsAppMessage,
    WhatsAppTextMessage,
    WhatsAppEntry,
    WhatsAppChange,
    WhatsAppValue,
)

# 7. API Response Models
from .responses import SuccessResponse, ErrorResponse, AvailableSlot

# This __all__ list defines what is exported when someone does 'from models import *'
__all__ = [
    "BookingStatus",
    "DayOfWeek",
    "User",
    "UserCreate",
    "UserUpdate",
    "Consultant",
    "ConsultantCreate",
    "ConsultantUpdate",
    "Availability",
    "AvailabilityCreate",
    "AvailabilityUpdate",
    "Booking",
    "BookingCreate",
    "BookingUpdate",
    "Message",
    "ConversationHistory",
    "ConversationHistoryCreate",
    "WhatsAppWebhookPayload",
    "WhatsAppMessage",
    "WhatsAppTextMessage",
    "WhatsAppEntry",
    "WhatsAppChange",
    "WhatsAppValue",
    "SuccessResponse",
    "ErrorResponse",
    "AvailableSlot",
]
