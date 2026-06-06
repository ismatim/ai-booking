import secrets
import string
from config import get_settings
from utils.logger import get_logger

settings = get_settings()

logger = get_logger(__name__)


class DecentralizedBookingID:
    def __init__(self):
        self.node_id = settings.node_id or "01"

        # remove IO characters from alphabet due to accesibility
        self.alphabet = "".join(
            c for c in string.ascii_uppercase + string.digits if c not in "IO"
        )

    def generate(self, suffix_length: int = 4) -> str:
        """Generates an ultra-compact decentralized booking ID without a year component."""

        # Selección segura del sufijo
        random_suffix = "".join(
            secrets.choice(self.alphabet) for _ in range(suffix_length)
        )

        # BK-[NODE][SUFFIX]
        return f"BK-{self.node_id}{random_suffix}"
