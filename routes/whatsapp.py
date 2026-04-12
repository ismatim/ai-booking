"""WhatsApp webhook router for AI Booking (Twilio & Meta Support)."""

from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Form
from fastapi.responses import PlainTextResponse, Response
from config import get_settings
from services.booking_service import BookingService
from services.gemini_service import GeminiService
from services.supabase_service import SupabaseService
from services.twilio_service import TwilioService
from services.meta_service import MetaService
from utils.logger import get_logger
from utils.validators import normalize_phone_number, validate_phone_number

from utils.timezone import format_readable_date

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

    # Return a valid, empty TwiML response to keep Twilio happy
    twiml = MessagingResponse()
    return Response(content=str(twiml), media_type="application/xml")


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

    # We check if this user is already 'bound' to a specific Financial Broker
    active_consultant_id = context.get("active_consultant_id")
    active_consultant = None

    if active_consultant_id:
        # Fetch the broker's metadata (name, services, bio) to give Gemini context
        logger.info(f"User {user_id} has active consultant {active_consultant_id}")
        active_consultant = db_svc.get_consultant(active_consultant_id)
    # ------------------------------------------

    if message_text.strip().upper().startswith("CANCEL "):
        reply = await _handle_cancel_command_logic(message_text, user_id)
        await messenger.send_text_message(phone, reply)
        return

    # Gemini reasoning turn
    user_context = {
        "user_name": sender_name,
        "language": user.get("language", "en"),
        "reschedule_id": context.get("reschedule_booking_id"),
        # We pass the broker info (or None) to the AI
        "active_consultant": active_consultant,
        "discovery_mode": active_consultant is None,
        "current_time": datetime.now(timezone.utc).isoformat(),
    }

    ai_result = await gemini_svc.process_message(
        user_message=message_text,
        conversation_history=history,
        user_context=user_context,
    )

    # Execute extracted action
    action = ai_result.get("action", "answer")
    data = ai_result.get("data", {})

    # The dispatcher now handles the 'switch' from Discovery to a specific Broker
    reply = await _dispatch_action(action, data, phone, user_id, context)

    # Send the reply
    if reply:
        await messenger.send_text_message(to=phone, body=reply)

    # Record the conversation history
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

    if action == "set_consultant":
        return await _handle_set_consultant(data, context)

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


async def _handle_set_consultant(data: Dict, context: Dict) -> str:
    name_query = data.get("consultant_name")
    # You'll build this in db_svc to search your 'consultants' table
    consultant = db_svc.find_consultant_by_name(name_query)

    if consultant:
        context["active_consultant_id"] = str(consultant["id"])
        return f"Perfect. I've connected you with {consultant['name']}. What can we do for you?"

    return f"I couldn't find a broker named {name_query}. Could you please double-check the name?"


async def _handle_check_availability(data: Dict, context: Dict) -> str:
    # Security & Identity Gate
    # Ensure we know which broker we are checking for
    consultant_id = context.get("active_consultant_id")
    if not consultant_id:
        return "I'd be happy to check availability! Could you tell me which Consultant you'd like to book with?"

    date_str = data.get("date")
    if not date_str:
        return "Which day would you like to check?"

    try:
        #  Parse and Query
        date = datetime.fromisoformat(date_str)

        # Pass the consultant_id to ensure we don't query the wrong calendar
        # Optionally pass 'service' if Gemini extracted it for duration logic
        slots = booking_svc.get_available_slots(date=date, consultant_id=consultant_id)

        if not slots:
            # Use your centralized logic
            readable_date = format_readable_date(date)
            return f"I'm sorry, there are no slots available for {readable_date}."

        # 4. State Management
        # Save slots in context so the User can just say "the first one" or "10am"
        context["pending_slots"] = slots

        # 5. Presentation
        # Ensure your format_slots_for_whatsapp also uses the time helpers!
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
