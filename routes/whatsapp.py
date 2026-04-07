"""WhatsApp webhook endpoints for AI Booking application."""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from config import get_settings
from services.booking_service import BookingService
from services.gemini_service import GeminiService
from services.supabase_service import SupabaseService
from services.whatsapp_service import WhatsAppService
from utils.logger import get_logger
from utils.validators import normalize_phone_number, validate_phone_number

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

# Singleton service instances (created once per worker)
whatsapp_svc = WhatsAppService()
gemini_svc = GeminiService()
booking_svc = BookingService()
db_svc = SupabaseService()

# Maximum number of messages to retain in conversation history
MAX_CONVERSATION_HISTORY = 20


# ---------------------------------------------------------------------------
# Webhook verification (GET)
# ---------------------------------------------------------------------------


@router.get("")
async def verify_webhook(request: Request) -> PlainTextResponse:
    """Handle Meta webhook verification challenge.

    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    We respond with the challenge value to confirm ownership.
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=challenge or "", status_code=200)

    logger.warning("WhatsApp webhook verification failed: token mismatch")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


# ---------------------------------------------------------------------------
# Incoming message handler (POST)
# ---------------------------------------------------------------------------


@router.post("")
async def receive_message(request: Request) -> Dict[str, str]:
    """Process incoming WhatsApp messages.

    Parses the webhook payload, routes to AI conversation engine, and
    dispatches the appropriate action (availability check, booking, etc.).
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.debug("WhatsApp webhook payload: %s", payload)

    # Ignore non-message events (e.g. status updates)
    if payload.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    phone = whatsapp_svc.extract_sender_phone(payload)
    message_text = whatsapp_svc.extract_message_text(payload)

    if not phone or not message_text:
        return {"status": "no_message"}

    # Normalise phone number
    phone = normalize_phone_number(phone)
    if not validate_phone_number(phone):
        logger.warning("Invalid phone number received (redacted)")
        return {"status": "invalid_phone"}

    sender_name = whatsapp_svc.extract_sender_name(payload)

    # Ensure user exists in our DB
    user = db_svc.get_or_create_user(phone_number=phone, name=sender_name)
    user_id = str(user["id"])

    logger.info("Message from user_id=%s: %s", user_id, message_text[:100])

    # Load conversation history
    history_record = db_svc.get_conversation(user_id)
    history = history_record["messages"] if history_record else []
    context = history_record["context"] if history_record else {}

    # Handle quick commands (CANCEL / RESCHEDULE) before AI routing
    if message_text.strip().upper().startswith("CANCEL "):
        await _handle_cancel_command(phone, message_text, user_id)
        return {"status": "ok"}

    if message_text.strip().upper().startswith("RESCHEDULE "):
        await _handle_reschedule_command(phone, message_text, user_id, history, context)
        return {"status": "ok"}

    # AI conversation routing
    user_context = {"user_name": user.get("name") or phone, "language": user.get("language", "en")}
    ai_result = await gemini_svc.process_message(
        user_message=message_text,
        conversation_history=history,
        user_context=user_context,
    )

    # Append messages to history
    history.append({"role": "user", "content": message_text, "timestamp": datetime.now(timezone.utc).isoformat()})
    history.append(
        {
            "role": "assistant",
            "content": ai_result.get("raw_response", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    action = ai_result.get("action", "answer")
    data = ai_result.get("data", {})

    reply = await _dispatch_action(action, data, phone, user_id, context)
    if reply:
        await whatsapp_svc.send_text_message(to=phone, body=reply)

    # Persist updated history
    db_svc.save_conversation(user_id=user_id, messages=history[-MAX_CONVERSATION_HISTORY:], context=context)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Action dispatcher
# ---------------------------------------------------------------------------


async def _dispatch_action(
    action: str,
    data: Dict[str, Any],
    phone: str,
    user_id: str,
    context: Dict[str, Any],
) -> str:
    """Route an AI action to the appropriate handler.

    Args:
        action: Action name from Gemini response.
        data: Action data dict.
        phone: Sender's phone number.
        user_id: Sender's user UUID string.
        context: Mutable conversation context dict.

    Returns:
        Reply text to send back to the user.
    """
    if action == "answer":
        return data.get("message", "")

    if action == "check_availability":
        return await _handle_check_availability(data, context)

    if action == "create_booking":
        return await _handle_create_booking(data, phone, user_id, context)

    if action == "cancel_booking":
        return await _handle_cancel_booking_action(data, user_id)

    if action == "reschedule_booking":
        return await _handle_reschedule_booking_action(data, user_id)

    if action == "view_bookings":
        return booking_svc.get_user_bookings_summary(user_id)

    # Unknown action – fall back to raw AI response
    return data.get("message", "")


async def _handle_check_availability(
    data: Dict[str, Any], context: Dict[str, Any]
) -> str:
    """Check available slots and store them in context for later selection."""
    date_str = data.get("date")
    if not date_str:
        return "Could you please specify a date? For example: 'next Monday' or '2026-04-10'."

    try:
        date = datetime.fromisoformat(date_str)
    except ValueError:
        return f"I couldn't parse the date '{date_str}'. Please use YYYY-MM-DD format or describe it naturally."

    consultant_id = data.get("consultant_id")
    slots = booking_svc.get_available_slots(date=date, consultant_id=consultant_id)

    if not slots:
        return (
            f"😔 No available slots found for {date.strftime('%A, %B %d')}. "
            "Would you like to check another day?"
        )

    # Store slots in context so the user can pick by number
    context["pending_slots"] = slots
    context["pending_date"] = date_str

    return booking_svc.format_slots_for_whatsapp(slots)


async def _handle_create_booking(
    data: Dict[str, Any],
    phone: str,
    user_id: str,
    context: Dict[str, Any],
) -> str:
    """Create a booking from AI-extracted parameters."""
    try:
        consultant_id = data["consultant_id"]
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = datetime.fromisoformat(data["end_time"])
    except (KeyError, ValueError) as exc:
        return f"I'm missing some booking details: {exc}. Could you clarify?"

    service = data.get("service")
    notes = data.get("notes")

    try:
        booking = booking_svc.create_booking(
            user_id=user_id,
            consultant_id=consultant_id,
            start_time=start_time,
            end_time=end_time,
            service=service,
            notes=notes,
        )
        context.pop("pending_slots", None)
        context.pop("pending_date", None)
        return booking_svc.build_booking_confirmation(booking)
    except ValueError as exc:
        return f"❌ Could not create booking: {exc}"
    except Exception as exc:
        logger.error("Unexpected error creating booking: %s", exc)
        return "❌ An unexpected error occurred. Please try again."


async def _handle_cancel_booking_action(data: Dict[str, Any], user_id: str) -> str:
    """Cancel a booking from AI-extracted parameters."""
    booking_id = data.get("booking_id")
    if not booking_id:
        return "Please provide the booking ID to cancel. Example: *CANCEL abc12345*"
    try:
        booking_svc.cancel_booking(booking_id, user_id=user_id)
        return "✅ Your booking has been successfully cancelled."
    except ValueError as exc:
        return f"❌ {exc}"


async def _handle_reschedule_booking_action(data: Dict[str, Any], user_id: str) -> str:
    """Reschedule a booking from AI-extracted parameters."""
    booking_id = data.get("booking_id")
    new_start = data.get("new_start_time")
    new_end = data.get("new_end_time")
    if not all([booking_id, new_start, new_end]):
        return "Please provide the booking ID and new time to reschedule."
    try:
        updated = booking_svc.reschedule_booking(
            booking_id=booking_id,
            new_start_time=datetime.fromisoformat(new_start),
            new_end_time=datetime.fromisoformat(new_end),
            user_id=user_id,
        )
        return f"✅ Booking rescheduled successfully!\n\n{booking_svc.build_booking_confirmation(updated)}"
    except ValueError as exc:
        return f"❌ {exc}"


# ---------------------------------------------------------------------------
# Quick command helpers
# ---------------------------------------------------------------------------


async def _handle_cancel_command(phone: str, message_text: str, user_id: str) -> None:
    """Handle direct CANCEL <booking_id> command."""
    parts = message_text.strip().split()
    if len(parts) < 2:
        reply = "Please provide a booking ID: *CANCEL <booking_id>*"
    else:
        short_id = parts[1]
        bookings = db_svc.get_bookings_by_user(user_id)
        match = next(
            (b for b in bookings if str(b["id"]).startswith(short_id) or str(b["id"]) == short_id),
            None,
        )
        if not match:
            reply = f"❌ No booking found with ID starting with '{short_id}'."
        else:
            try:
                booking_svc.cancel_booking(str(match["id"]), user_id=user_id)
                reply = "✅ Your booking has been successfully cancelled."
            except ValueError as exc:
                reply = f"❌ {exc}"
    await whatsapp_svc.send_text_message(to=phone, body=reply)


async def _handle_reschedule_command(
    phone: str,
    message_text: str,
    user_id: str,
    history: list,
    context: Dict[str, Any],
) -> None:
    """Handle direct RESCHEDULE <booking_id> command by prompting for new time."""
    parts = message_text.strip().split()
    if len(parts) < 2:
        reply = "Please provide a booking ID: *RESCHEDULE <booking_id>*"
    else:
        short_id = parts[1]
        bookings = db_svc.get_bookings_by_user(user_id)
        match = next(
            (b for b in bookings if str(b["id"]).startswith(short_id) or str(b["id"]) == short_id),
            None,
        )
        if not match:
            reply = f"❌ No booking found with ID starting with '{short_id}'."
        else:
            context["reschedule_booking_id"] = str(match["id"])
            reply = (
                "📅 What date and time would you like to reschedule to?\n"
                "Please tell me a date and time, e.g. 'next Thursday at 2pm'."
            )
    await whatsapp_svc.send_text_message(to=phone, body=reply)
