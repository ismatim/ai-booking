"""Configuration management for AI Booking application."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


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

    # Google Calendar
    google_calendar_credentials: Optional[str] = None  # JSON string or file path
    google_calendar_token: Optional[str] = None  # JSON string for OAuth token

    # Scheduler
    reminder_check_interval_minutes: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
