"""FastAPI application entry point for AI Booking."""

import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routes import admin, bookings, consultants, whatsapp, auth
from services.reminder_service import ReminderService
from utils.logger import get_logger
from starlette.middleware.sessions import SessionMiddleware

settings = get_settings()
logger = get_logger(__name__)

reminder_service = ReminderService()

# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    reminder_service.start()
    yield
    logger.info("Shutting down %s", settings.app_name)
    reminder_service.stop()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered WhatsApp appointment booking system using "
        "Google Gemini, Meta WhatsApp Business API, and Supabase."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        settings.fast_api_auth_session_secret_key, settings.fast_api_auth_secret_key
    ),
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(whatsapp.router)
app.include_router(bookings.router)
app.include_router(consultants.router)
app.include_router(admin.router)
app.include_router(auth.router)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Return application health status, or redirect browser to the dashboard."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "dashboard": "http://localhost:3000",
    }


@app.get("/health", tags=["Health"])
async def health() -> Dict[str, str]:
    """Detailed health endpoint."""
    return {"status": "ok"}
