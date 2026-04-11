"""Google Gemini AI conversation service for AI Booking application."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types  # Ensure this is imported at the top

from config import get_settings
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# System prompt for booking assistant
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are the professional Concierge for a Financial Brokerage Firm. 
Your goal is to connect clients with the right Financial Broker and manage their appointments.

Current Context:
- Active Broker: {active_consultant} (If null, you are in 'Firm Concierge' mode. If set, you are acting as their personal assistant).

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
- Support the user's language (English/Spanish/etc).
- If the broker mentioned is not found, stay in Concierge mode and ask for clarification.

When you need to take an action, respond with a JSON object (and nothing else) in this format:
{{
  "action": "<action_name>",
  "data": {{ ... }},
  "raw_response": "Friendly WhatsApp message here"
}}

Available actions:
- "set_consultant": data = {{"consultant_name": "extracted_name"}} -> Use when user identifies a broker.
- "check_availability": data = {{"date": "YYYY-MM-DD", "time_preference": "morning|afternoon|evening|any", "consultant_id": "optional-uuid"}}
- "create_booking": data = {{"consultant_id": "uuid", "start_time": "ISO8601", "end_time": "ISO8601", "service": "optional", "notes": "optional"}}
- "cancel_booking": data = {{"booking_id": "uuid"}}
- "reschedule_booking": data = {{"booking_id": "uuid", "new_start_time": "ISO8601", "new_end_time": "ISO8601"}}
- "view_bookings": data = {{}}
- "answer": data = {{"message": "your response text to the user"}}

When responding to the user (not taking an action), use the "answer" action format.
"""


class GeminiService:
    """Manages multi-turn AI conversations using the modern Google Gen AI SDK."""

    def __init__(self) -> None:
        # Initialize the persistent client
        # It automatically picks up the GEMINI_API_KEY from environment variables
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_id = settings.gemini_model or "gemini-2.5-flash"

    def _build_system_prompt(self) -> str:
        """Injects current time context into the system prompt."""
        return SYSTEM_PROMPT.format(
            today=datetime.now(timezone.utc).strftime("%A, %B %d %Y"),
            timezone=settings.timezone,
            current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _format_history(self, messages: List[Dict[str, Any]]) -> List[types.Content]:
        """
        Convert standard history dicts into SDK-specific types.Content objects.
        Filters out 'system' messages to avoid duplicates with the system_instruction.
        """
        history = []
        for msg in messages:
            # 1. Skip system messages in history
            # (We already pass the system prompt in the config)
            if msg["role"] == "system":
                continue

            # 2. Map roles: 'assistant' (from DB) -> 'model' (for Gemini)
            role = "user" if msg["role"] == "user" else "model"

            # 3. Handle potential empty content gracefully
            content_text = msg.get("content", "")
            if not content_text:
                continue

            history.append(
                types.Content(
                    role=role, parts=[types.Part.from_text(text=content_text)]
                )
            )
        return history

    async def process_message(
        self,
        user_message: str,
        conversation_history: List[Dict],
        user_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sends the message to Gemini using the new 2.0 Client SDK.
        """
        # 1. Prepare System Instruction
        system_instruction = SYSTEM_PROMPT.format(
            today=user_context.get("current_time"),
            timezone=user_context.get("timezone", "UTC"),
            active_consultant=json.dumps(user_context.get("active_consultant")),
        )

        # 2. Convert history using your existing helper _format_history
        # This turns your dicts into the required types.Content objects
        history = self._format_history(conversation_history)

        # 3. Configure the generation (JSON mode + System Prompt)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            response_mime_type="application/json",
        )

        try:
            # 4. Use the async client (aio) to generate content
            # We pass history + the current message as the 'contents'
            response = await self.client.aio.models.generate_content(
                model=self.model_id, contents=history + [user_message], config=config
            )

            # 5. Parse JSON
            ai_data = json.loads(response.text)

            return {
                "action": ai_data.get("action", "answer"),
                "data": ai_data.get("data", {}),
                "raw_response": ai_data.get("raw_response", "I'm here to help."),
            }

        except Exception as e:
            logger.error(f"Gemini Service Error: {e}")
            return {
                "action": "answer",
                "data": {},
                "raw_response": "Sorry, I hit a snag.",
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
