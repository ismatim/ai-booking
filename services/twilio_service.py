# services/twilio_service.py
from twilio.rest import Client
from .base_whatsapp import BaseWhatsAppService
from config import get_settings
from utils.logger import get_logger

from twilio.base.exceptions import TwilioRestException

logger = get_logger(__name__)

settings = get_settings()


class TwilioService(BaseWhatsAppService):
    def __init__(self):
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        raw_num = str(settings.twilio_whatsapp_number).replace("whatsapp:", "").strip()
        if not raw_num.startswith("+"):
            raw_num = f"+{raw_num}"

        self.from_phone = f"whatsapp:{raw_num}"
        logger.info(f"DEBUG: Twilio Sender is set to -> '{self.from_phone}'")
        # self.from_phone = f"whatsapp:{settings.twilio_whatsapp_number}"

    async def send_text_message(self, to: str, body: str):
        """Sends a WhatsApp message with proper prefix and error handling."""
        try:
            # Ensure 'to' has the whatsapp: prefix
            formatted_to = to if to.startswith("whatsapp:") else f"whatsapp:{to}"

            # Ensure your 'from' (the broker's twilio number) also has it
            formatted_from = (
                self.from_phone
                if self.from_phone.startswith("whatsapp:")
                else f"whatsapp:{self.from_phone}"
            )

            message = self.client.messages.create(
                body=body, from_=formatted_from, to=formatted_to
            )
            return message.sid

        except TwilioRestException as e:
            # This will print the EXACT Twilio error code (e.g., 21608 or 63003)
            print(
                f"❌ Twilio Error: Status {e.status} | Code {e.code} | Message: {e.msg}"
            )
            return None

    def extract_sender(self, form_data: dict):
        """Twilio sends Form Data, not JSON."""
        return {
            "phone": form_data.get("From", "").replace("whatsapp:", ""),
            "message": form_data.get("Body", ""),
            "name": form_data.get("ProfileName", "User"),
        }
