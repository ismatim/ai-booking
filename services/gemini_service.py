"""Google Gemini AI conversation service for AI Booking application."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import google.generativeai as genai

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
    """Manages multi-turn AI conversations using Google Gemini."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model,
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current date/time injected."""
        return SYSTEM_PROMPT.format(
            today=datetime.now(timezone.utc).strftime("%A, %B %d %Y"),
            timezone=settings.timezone,
        )

    def _format_history_for_gemini(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert stored message history to Gemini chat format.

        Args:
            messages: List of {'role': str, 'content': str} dicts.

        Returns:
            List of Gemini-compatible message dicts.
        """
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg["content"]]})
        return gemini_messages

    async def process_message(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a user message and return an AI response.

        Args:
            user_message: The user's latest message text.
            conversation_history: Previous messages in the conversation.
            user_context: Optional context dict (user name, language, etc.).

        Returns:
            Dict with 'action', 'data', and 'raw_response' keys.
        """
        system = self._build_system_prompt()
        if user_context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in user_context.items())
            system += f"\n\nUser context:\n{context_str}"

        history = self._format_history_for_gemini(conversation_history)

        try:
            chat = self.model.start_chat(history=history)
            # Prepend system instruction to the first turn
            if not history:
                full_message = f"{system}\n\nUser: {user_message}"
            else:
                full_message = user_message

            response = chat.send_message(full_message)
            raw_text = response.text.strip()
            logger.debug("Gemini raw response: %s", raw_text)

            return self._parse_response(raw_text)

        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            return {
                "action": "answer",
                "data": {
                    "message": "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment."
                },
                "raw_response": str(exc),
            }

    def _parse_response(self, raw_text: str) -> Dict[str, Any]:
        """Parse Gemini response – either JSON action or plain text.

        Args:
            raw_text: Raw response string from Gemini.

        Returns:
            Parsed action dict.
        """
        # Try to extract JSON from the response
        json_start = raw_text.find("{")
        json_end = raw_text.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            json_str = raw_text[json_start:json_end]
            try:
                parsed = json.loads(json_str)
                if "action" in parsed and "data" in parsed:
                    parsed["raw_response"] = raw_text
                    return parsed
            except json.JSONDecodeError:
                pass

        # Fallback: treat entire response as a plain answer
        return {
            "action": "answer",
            "data": {"message": raw_text},
            "raw_response": raw_text,
        }

    async def detect_language(self, text: str) -> str:
        """Detect the language of the given text using Gemini.

        Args:
            text: Text to analyse.

        Returns:
            BCP-47 language code string (e.g. 'en', 'fr', 'es').
        """
        prompt = (
            f"Detect the language of the following text and respond with only the BCP-47 "
            f"language code (e.g. 'en', 'fr', 'es', 'ar'). Text: '{text}'"
        )
        try:
            response = self.model.generate_content(prompt)
            code = response.text.strip().lower().split()[0]
            # Return first token up to 5 chars to handle codes like 'en-US'
            return code[:5]
        except Exception as exc:
            logger.warning("Language detection failed: %s", exc)
            return "en"
