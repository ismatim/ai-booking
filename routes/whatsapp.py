from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Form
from fastapi.responses import PlainTextResponse, Response
from config import get_settings
from services.booking_service import BookingService

from services.twilio_service import TwilioService
from services.meta_service import MetaService
from services.langchain_service import LangChainService
from utils.logger import get_logger
from utils.validators import normalize_phone_number, validate_phone_number

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])

# --- Service Initializations ---
twilio_svc = TwilioService()
meta_svc = MetaService()
langchain_svc = LangChainService()

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
    ConversationSid: Optional[str] = Form(None),
):
    """Handle incoming Twilio (Form-Data) payloads."""
    # Twilio format is 'whatsapp:+123456789'
    phone = From.replace("whatsapp:", "")

    if phone and Body:
        background_tasks.add_task(
            process_inbound_logic, phone, Body, ProfileName, twilio_svc, ConversationSid
        )

    # Return a valid, empty TwiML response to keep Twilio happy
    twiml = MessagingResponse()
    return Response(content=str(twiml), media_type="application/xml")


# ---------------------------------------------------------------------------
# Core Processing Pipeline (The Unified Engine)
# ---------------------------------------------------------------------------
async def process_inbound_logic(
    phone: str,
    message_text: str,
    sender_name: str,
    messenger: Any,
    conversation_sid: Optional[str] = None,
):
    """
    The orchestrator: validates metadata, transfers execution straight to
    the stateful LangGraph workflow, and forwards the generated response.
    """
    # 1. Clean and normalize the identifier
    phone = normalize_phone_number(phone)
    if not validate_phone_number(phone):
        logger.warning(f"Invalid phone number verification failed: {phone}")
        return

    # 2. Select the thread isolation key (thread_id)
    # If it's a Twilio group conversation, we isolate state by ConversationSid, otherwise by Phone
    thread_id = conversation_sid if conversation_sid else phone

    logger.info(f"Processing message from thread_id: {thread_id}")

    try:
        # 3. Hand off to LangGraph
        # SQLite automatically updates state, resolves history, and runs tools dynamically
        final_ai_reply = await langchain_svc.process_message(
            user_message=message_text, thread_id=thread_id, sender_name=sender_name
        )

        # 4. Fire the clean response string back to WhatsApp
        if settings.environment == "production":
            if final_ai_reply:
                await messenger.send_text_message(to=phone, body=final_ai_reply)
        else:
            logger.info(f"DEV MODE: Skipping WhatsApp response: {final_ai_reply}")

    except Exception as e:
        logger.error(
            f"Error executing processing pipeline for thread {thread_id}: {str(e)}",
            exc_info=True,
        )
