# services/twilio_service.py
from twilio.rest import Client
from .base_whatsapp import BaseWhatsAppService
from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()


class TwilioService(BaseWhatsAppService):
    def __init__(self):
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self.from_number = f"whatsapp:{settings.twilio_whatsapp_number}"

    async def send_text_message(self, to: str, body: str):
        # Twilio needs the whatsapp: prefix
        formatted_to = to
        if not formatted_to.startswith("whatsapp:"):
            if not formatted_to.startswith("+"):
                formatted_to = f"+{formatted_to}"
            formatted_to = f"whatsapp:{formatted_to}"

        try:
            return self.client.messages.create(
                body=body, from_=self.from_number, to=formatted_to
            )

        except Exception as e:
            logger.error("Twilio API send message error: %s", e)
            raise

    def extract_sender(self, form_data: dict):
        """Twilio sends Form Data, not JSON."""
        return {
            "phone": form_data.get("From", "").replace("whatsapp:", ""),
            "message": form_data.get("Body", ""),
            "name": form_data.get("ProfileName", "User"),
        }
