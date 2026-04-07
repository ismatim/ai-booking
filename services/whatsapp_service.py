"""Meta WhatsApp Business API integration."""

from typing import Any, Dict, List, Optional

import httpx

from config import get_settings
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

WHATSAPP_API_BASE = "https://graph.facebook.com"


class WhatsAppService:
    """Handles sending messages through the Meta WhatsApp Business API."""

    def __init__(self) -> None:
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.token = settings.whatsapp_token
        self.api_version = settings.whatsapp_api_version
        self.base_url = f"{WHATSAPP_API_BASE}/{self.api_version}/{self.phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Text messages
    # ------------------------------------------------------------------

    async def send_text_message(self, to: str, body: str) -> Dict[str, Any]:
        """Send a plain text WhatsApp message.

        Args:
            to: Recipient phone number (digits only, no '+').
            body: Message text (max 4096 characters).

        Returns:
            API response dict.
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        return await self._post(payload)

    async def send_interactive_buttons(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an interactive message with quick-reply buttons (max 3).

        Args:
            to: Recipient phone number.
            body_text: Main message body.
            buttons: List of dicts with 'id' and 'title' keys.
            header_text: Optional header text.
            footer_text: Optional footer text.

        Returns:
            API response dict.
        """
        button_items = [
            {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
            for b in buttons[:3]
        ]
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": button_items},
            },
        }
        if header_text:
            payload["interactive"]["header"] = {"type": "text", "text": header_text}
        if footer_text:
            payload["interactive"]["footer"] = {"text": footer_text}
        return await self._post(payload)

    async def send_interactive_list(
        self,
        to: str,
        body_text: str,
        button_label: str,
        sections: List[Dict[str, Any]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an interactive list message.

        Args:
            to: Recipient phone number.
            body_text: Main message body.
            button_label: Label for the list-open button (max 20 chars).
            sections: List of section dicts with 'title' and 'rows'.
            header_text: Optional header text.
            footer_text: Optional footer text.

        Returns:
            API response dict.
        """
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body_text},
                "action": {"button": button_label, "sections": sections},
            },
        }
        if header_text:
            payload["interactive"]["header"] = {"type": "text", "text": header_text}
        if footer_text:
            payload["interactive"]["footer"] = {"text": footer_text}
        return await self._post(payload)

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "en_US",
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send a pre-approved WhatsApp template message.

        Args:
            to: Recipient phone number.
            template_name: Approved template name.
            language_code: BCP-47 language code (default 'en_US').
            components: Optional template component parameters.

        Returns:
            API response dict.
        """
        template: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template["components"] = components
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template,
        }
        return await self._post(payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an HTTP POST to the WhatsApp API.

        Args:
            payload: JSON-serialisable request body.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: If the API returns a non-2xx status.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.debug("WhatsApp API response: %s", response.text)
            return response.json()

    def extract_message_text(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract the text body from a raw webhook payload.

        Args:
            payload: Raw WhatsApp webhook JSON dict.

        Returns:
            Message text string, or None if not a text message.
        """
        try:
            entries = payload.get("entry", [])
            for entry in entries:
                for change in entry.get("changes", []):
                    messages = change.get("value", {}).get("messages", [])
                    for msg in messages:
                        if msg.get("type") == "text":
                            return msg["text"]["body"]
                        if msg.get("type") == "interactive":
                            interactive = msg.get("interactive", {})
                            if interactive.get("type") == "button_reply":
                                return interactive["button_reply"]["title"]
                            if interactive.get("type") == "list_reply":
                                return interactive["list_reply"]["title"]
        except (KeyError, TypeError) as exc:
            logger.warning("Failed to extract message text: %s", exc)
        return None

    def extract_sender_phone(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract the sender's phone number from a raw webhook payload.

        Args:
            payload: Raw WhatsApp webhook JSON dict.

        Returns:
            Sender's phone number string, or None.
        """
        try:
            entries = payload.get("entry", [])
            for entry in entries:
                for change in entry.get("changes", []):
                    messages = change.get("value", {}).get("messages", [])
                    if messages:
                        return messages[0].get("from")
        except (KeyError, TypeError) as exc:
            logger.warning("Failed to extract sender phone: %s", exc)
        return None

    def extract_sender_name(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract the sender's display name from a raw webhook payload.

        Args:
            payload: Raw WhatsApp webhook JSON dict.

        Returns:
            Sender's display name, or None.
        """
        try:
            entries = payload.get("entry", [])
            for entry in entries:
                for change in entry.get("changes", []):
                    contacts = change.get("value", {}).get("contacts", [])
                    if contacts:
                        return contacts[0].get("profile", {}).get("name")
        except (KeyError, TypeError) as exc:
            logger.warning("Failed to extract sender name: %s", exc)
        return None
