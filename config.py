"""Configuration management for AI Booking application using Pydantic V2."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "AI Booking"
    app_version: str = "1.0.0"
    debug: bool = False
    timezone: str = "UTC"

    # WhatsApp / Meta Business API
    whatsapp_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str = "ai_booking_verify_token"
    whatsapp_api_version: str = "v18.0"

    # Google Gemini AI
    gemini_api_key: str
    gemini_model: str = "gemini-1.5-flash"

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_password: str
    # This is the psycopg2 connection string (Port 6543)
    supabase_conn: str

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

    # Scheduler
    reminder_check_interval_minutes: int = 5

    # Cryptography
    encryption_key: str
    fast_api_auth_session_secret_key: str
    fast_api_auth_secret_key: str

    # --- Pydantic V2 Configuration ---
    # This replaces the old 'class Config'
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Prevents crashing if .env has extra helper variables
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings (Singleton)."""
    return Settings()
