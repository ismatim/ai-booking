"""Google Gemini AI conversation service for AI Booking application."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from config import get_settings
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# System prompt for booking assistant
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a friendly and professional AI appointment booking assistant for a consulting service.

Your responsibilities:
1. Help users book, reschedule, or cancel appointments via WhatsApp
2. Understand natural language date/time requests (e.g. "next Tuesday afternoon", "this Friday at 3pm")
3. Collect all required booking information: preferred date/time, service type, any special notes
4. Confirm bookings and provide clear summaries
5. Answer questions about services, pricing, and consultant availability
6. Support multiple languages - always respond in the same language the user uses

Booking flow:
1. Greet the user and ask what they need
2. If booking: ask for preferred date/time and service
3. Show available slots for requested time period
4. Confirm booking details before finalizing
5. Provide booking confirmation with details

Important guidelines:
- Be concise and clear in WhatsApp messages (avoid very long responses)
- Use emojis sparingly for a friendly tone
- Always confirm details before finalizing a booking
- If a date/time is unclear, ask for clarification
- Today's date is: {today}
- Timezone: {timezone}

When you need to take an action, respond with a JSON object (and nothing else) in this format:
{
  "action": "<action_name>",
  "data": { ... }
}

Available actions:
- "check_availability": data = {"date": "YYYY-MM-DD", "time_preference": "morning|afternoon|evening|any", "consultant_id": "optional-uuid"}
- "create_booking": data = {"consultant_id": "uuid", "start_time": "ISO8601", "end_time": "ISO8601", "service": "optional", "notes": "optional"}
- "cancel_booking": data = {"booking_id": "uuid"}
- "reschedule_booking": data = {"booking_id": "uuid", "new_start_time": "ISO8601", "new_end_time": "ISO8601"}
- "view_bookings": data = {}
- "answer": data = {"message": "your response text to the user"}

When responding to the user (not taking an action), use the "answer" action format.
"""


class GeminiService:
    """Manages multi-turn AI conversations using the modern Google Gen AI SDK."""

    def __init__(self) -> None:
        # Initialize the persistent client
        # It automatically picks up the GEMINI_API_KEY from environment variables
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_id = settings.gemini_model or "gemini-2.0-flash"

    def _build_system_prompt(self) -> str:
        """Injects current time context into the system prompt."""
        return SYSTEM_PROMPT.format(
            today=datetime.now(timezone.utc).strftime("%A, %B %d %Y"),
            timezone=settings.timezone,
        )

    def _format_history(self, messages: List[Dict[str, Any]]) -> List[types.Content]:
        """Convert standard history dicts into SDK-specific types.Content objects."""
        history = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            history.append(
                types.Content(
                    role=role, parts=[types.Part.from_text(text=msg["content"])]
                )
            )
        return history

    async def process_message(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process message using the aio (async) client to prevent blocking."""

        # Prepare the system instruction
        sys_instr = self._build_system_prompt()
        if user_context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in user_context.items())
            sys_instr += f"\n\nUser context:\n{context_str}"

        history = self._format_history(conversation_history)

        try:
            # 1. Create a chat session with dedicated system instructions
            # We use the .aio namespace for asynchronous operations
            chat = self.client.aio.chats.create(
                model=self.model_id,
                history=history,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instr,
                    temperature=0.3,
                ),
            )

            # 2. Send the message asynchronously
            response = await chat.send_message(user_message)
            raw_text = response.text.strip()

            logger.debug("Gemini response: %s", raw_text)
            return self._parse_response(raw_text)

        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            return {
                "action": "answer",
                "data": {
                    "message": "I'm having a bit of trouble thinking right now. Could you try that again?"
                },
                "raw_response": str(exc),
            }

    def _parse_response(self, raw_text: str) -> Dict[str, Any]:
        """Extracts JSON action from raw text, with safety fallback."""
        try:
            # Look for the JSON block in case the AI added commentary
            json_start = raw_text.find("{")
            json_end = raw_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                clean_json = raw_text[json_start:json_end]
                parsed = json.loads(clean_json)

                if "action" in parsed:
                    parsed["raw_response"] = raw_text
                    return parsed

        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback to a standard answer if parsing fails
        return {
            "action": "answer",
            "data": {"message": raw_text},
            "raw_response": raw_text,
        }

    async def detect_language(self, text: str) -> str:
        """Fast language detection using the async model interface."""
        prompt = f"Respond ONLY with the BCP-47 language code for this text: '{text}'"
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id, contents=prompt
            )
            return response.text.strip().lower()[:5]
        except Exception:
            return "en"
