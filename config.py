"""Configuration management for AI Booking application using Pydantic V2."""

import os
import sys

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    environment: str = os.getenv("APP_ENV", "development")
    default_timezone: str = "America/Argentina/Buenos_Aires"

    # Database
    database_filename: Path = project_root / "app.db"

    # Application
    app_name: str = "AI Booking"
    app_version: str = "0.0.1"
    debug: bool = False
    timezone: str = "UTC"

    env: str

    # WhatsApp / Meta Business API
    whatsapp_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str = "ai_booking_verify_token"
    whatsapp_api_version: str = "v18.0"

    # OpenAI
    openai_api_key: str
    openai_model: str

    # Google Calendar
    google_calendar_credentials: Optional[str] = None  # JSON string or file path
    google_calendar_token: Optional[str] = None  # JSON string for OAuth token
    google_calendar_client_id: str
    google_calendar_client_secret: str
    google_callback_url: str

    # Twilio Service
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_number: str

    # Scheduler Service
    reminder_start: bool = False
    reminder_check_interval_minutes: int = 5

    # Cryptography
    encryption_key: str
    fast_api_auth_session_secret_key: str
    fast_api_auth_secret_key: str

    # Integration

    integration_test_consultant_id: Optional[str] = (
        None  # UUID of a test consultant for integration tests
    )
    integration_target_calendar_id: Optional[str] = (
        None  # Calendar ID for integration tests
    )
    integration_scopes: Optional[str] = (
        None  # Comma-separated scopes for integration tests
    )

    # LangSmith
    langsmith_tracing: bool = False
    langsmith_endpoint: Optional[str] = None
    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = None

    # --- Pydantic V2 Configuration ---
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.integration"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Prevents crashing if .env has extra helper variables
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings (Singleton)."""
    return Settings()
