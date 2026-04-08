"""WhatsApp webhook router for AI Booking (Twilio & Meta Support)."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Form
from fastapi.responses import PlainTextResponse

from config import get_settings
from services.booking_service import BookingService
from services.gemini_service import GeminiService
from services.supabase_service import SupabaseService
from services.twilio_service import TwilioService
from services.meta_service import MetaService
from utils.logger import get_logger
from utils.validators import normalize_phone_number, validate_phone_number

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

# --- Service Initializations ---
twilio_svc = TwilioService()
meta_svc = MetaService()
gemini_svc = GeminiService()
booking_svc = BookingService()
db_svc = SupabaseService()

MAX_CONVERSATION_HISTORY = 20

# ---------------------------------------------------------------------------
# Endpoints (The Entry Points)
# ---------------------------------------------------------------------------


@router.get("/meta")
async def verify_meta_webhook(request: Request) -> PlainTextResponse:
    """Handle Meta's one-time webhook verification handshake."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Meta webhook verified successfully")
        return PlainTextResponse(content=challenge or "", status_code=200)

    logger.warning("Meta webhook verification failed: token mismatch")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/meta")
async def receive_meta_message(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming Meta (JSON) payloads."""
    payload = await request.json()

    if payload.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    phone = meta_svc.extract_sender_phone(payload)
    message = meta_svc.extract_message_text(payload)
    name = meta_svc.extract_sender_name(payload) or "User"

    if phone and message:
        background_tasks.add_task(process_inbound_logic, phone, message, name, meta_svc)

    return {"status": "ok"}


@router.post("/twilio")
async def receive_twilio_message(
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form("User"),
):
    """Handle incoming Twilio (Form-Data) payloads."""
    # Twilio format is 'whatsapp:+123456789'
    phone = From.replace("whatsapp:", "")

    if phone and Body:
        background_tasks.add_task(
            process_inbound_logic, phone, Body, ProfileName, twilio_svc
        )

    return ""  # Twilio accepts an empty body


# ---------------------------------------------------------------------------
# Core Processing Pipeline
# ---------------------------------------------------------------------------


async def process_inbound_logic(
    phone: str, message_text: str, sender_name: str, messenger: Any
):
    """The 'Brain' of the app: processes messages, calls AI, and replies."""
    phone = normalize_phone_number(phone)
    if not validate_phone_number(phone):
        logger.warning(f"Invalid phone number: {phone}")
        return

    # 1. Identity Management
    user = db_svc.get_or_create_user(phone_number=phone, name=sender_name)
    user_id = str(user["id"])

    history_record = db_svc.get_conversation(user_id)
    history = history_record.get("messages", []) if history_record else []
    context = history_record.get("context", {}) if history_record else {}

    # 2. Command Interception (Shortcuts)
    if message_text.strip().upper().startswith("CANCEL "):
        reply = await _handle_cancel_command_logic(message_text, user_id)
        await messenger.send_text_message(phone, reply)
        return

    if message_text.strip().upper().startswith("RESCHEDULE "):
        reply = await _handle_reschedule_command_logic(message_text, user_id, context)
        await messenger.send_text_message(phone, reply)
        db_svc.save_conversation(user_id, history, context)
        return

    # 3. AI Reasoning Turn
    user_context = {
        "user_name": sender_name,
        "language": user.get("language", "en"),
        "reschedule_id": context.get("reschedule_booking_id"),
    }

    ai_result = await gemini_svc.process_message(
        user_message=message_text,
        conversation_history=history,
        user_context=user_context,
    )

    # 4. Execute Extracted Action
    action = ai_result.get("action", "answer")
    data = ai_result.get("data", {})

    reply = await _dispatch_action(action, data, phone, user_id, context)

    # 5. Send the Reply via the triggering messenger (Twilio or Meta)
    if reply:
        await messenger.send_text_message(to=phone, body=reply)

    # 6. Record the Conversation history
    history.append(
        {
            "role": "user",
            "content": message_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    history.append(
        {
            "role": "assistant",
            "content": ai_result.get("raw_response", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    db_svc.save_conversation(
        user_id=user_id, messages=history[-MAX_CONVERSATION_HISTORY:], context=context
    )


# ---------------------------------------------------------------------------
# Action Dispatchers & Handlers
# ---------------------------------------------------------------------------


async def _dispatch_action(
    action: str, data: Dict, phone: str, user_id: str, context: Dict
) -> str:
    """Routes the AI's intent to the specific business logic handler."""
    if action == "answer":
        return data.get("message", "How can I help you today?")

    if action == "check_availability":
        return await _handle_check_availability(data, context)

    if action == "create_booking":
        return await _handle_create_booking(data, user_id, context)

    if action == "cancel_booking":
        return await _handle_cancel_booking_action(data, user_id)

    if action == "reschedule_booking":
        return await _handle_reschedule_booking_action(data, user_id)

    if action == "view_bookings":
        return booking_svc.get_user_bookings_summary(user_id)

    return data.get("message", "I'm not sure how to do that yet.")


async def _handle_check_availability(data: Dict, context: Dict) -> str:
    date_str = data.get("date")
    if not date_str:
        return "Which day would you like to check?"

    try:
        date = datetime.fromisoformat(date_str)
        slots = booking_svc.get_available_slots(date=date)

        if not slots:
            return f"No slots available for {date.strftime('%A, %B %d')}."

        # Save slots in context so the AI/User can reference them
        context["pending_slots"] = slots
        return booking_svc.format_slots_for_whatsapp(slots)
    except Exception as e:
        logger.error(f"Availability error: {e}")
        return "I had trouble checking the calendar. Could you try a different date?"


async def _handle_create_booking(data: Dict, user_id: str, context: Dict) -> str:
    try:
        booking = booking_svc.create_booking(
            user_id=user_id,
            consultant_id=data["consultant_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            service=data.get("service", "Consultation"),
        )
        # Clear booking state from context
        context.pop("pending_slots", None)
        return booking_svc.build_booking_confirmation(booking)
    except Exception as e:
        return f"Sorry, I couldn't finish that booking: {str(e)}"


async def _handle_cancel_booking_action(data: Dict, user_id: str) -> str:
    booking_id = data.get("booking_id")
    try:
        booking_svc.cancel_booking(booking_id, user_id=user_id)
        return "✅ Success! Your appointment has been cancelled."
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def _handle_reschedule_booking_action(data: Dict, user_id: str) -> str:
    try:
        updated = booking_svc.reschedule_booking(
            booking_id=data["booking_id"],
            new_start_time=datetime.fromisoformat(data["new_start_time"]),
            new_end_time=datetime.fromisoformat(data["new_end_time"]),
            user_id=user_id,
        )
        return f"✅ Rescheduled!\n\n{booking_svc.build_booking_confirmation(updated)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ---------------------------------------------------------------------------
# Manual Command Logic (Shortcuts)
# ---------------------------------------------------------------------------


async def _handle_cancel_command_logic(message_text: str, user_id: str) -> str:
    parts = message_text.strip().split()
    if len(parts) < 2:
        return "Please provide the ID: *CANCEL <id>*"

    short_id = parts[1]
    bookings = db_svc.get_bookings_by_user(user_id)
    match = next((b for b in bookings if str(b["id"]).startswith(short_id)), None)

    if not match:
        return "❌ Booking not found."

    try:
        booking_svc.cancel_booking(str(match["id"]), user_id=user_id)
        return "✅ Appointment cancelled."
    except ValueError as e:
        return f"❌ {str(e)}"


async def _handle_reschedule_command_logic(
    message_text: str, user_id: str, context: Dict
) -> str:
    parts = message_text.strip().split()
    if len(parts) < 2:
        return "Please provide the ID: *RESCHEDULE <id>*"

    short_id = parts[1]
    bookings = db_svc.get_bookings_by_user(user_id)
    match = next((b for b in bookings if str(b["id"]).startswith(short_id)), None)

    if not match:
        return "❌ Booking not found."

    context["reschedule_booking_id"] = str(match["id"])
    return "📅 Got it. What's the new date and time you're looking for?"

