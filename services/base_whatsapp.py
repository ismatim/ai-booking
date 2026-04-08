# services/base_whatsapp.py
from abc import ABC, abstractmethod


class BaseWhatsAppService(ABC):
    @abstractmethod
    async def send_text_message(self, to: str, body: str):
        pass

    @abstractmethod
    def extract_sender(self, payload: any):
        pass
