# services/twilio_service.py
from twilio.rest import Client
from .base_whatsapp import BaseWhatsAppService
from config import get_settings

settings = get_settings()


class TwilioService(BaseWhatsAppService):
    def __init__(self):
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self.from_number = f"whatsapp:{settings.twilio_whatsapp_number}"

    async def send_text_message(self, to: str, body: str):
        # Twilio needs the whatsapp: prefix
        to_formatted = f"whatsapp:{to}" if "whatsapp:" not in to else to
        return self.client.messages.create(
            body=body, from_=self.from_number, to=to_formatted
        )

    def extract_sender(self, form_data: dict):
        """Twilio sends Form Data, not JSON."""
        return {
            "phone": form_data.get("From", "").replace("whatsapp:", ""),
            "message": form_data.get("Body", ""),
            "name": form_data.get("ProfileName", "User"),
        }
