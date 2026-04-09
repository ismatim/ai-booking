from google_auth_oauthlib.flow import Flow
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from database import get_supabase

from utils.logger import get_logger

logger = get_logger(__name__)

db = get_supabase()
router = APIRouter(prefix="/auth", tags=["Bookings"])


@router.get("/google")
async def auth_google(consultant_id: str):
    flow = Flow.from_client_secrets_file(
        "client_secrets.json",
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        redirect_uri="https://your-api.com/auth/callback",
    )

    # We pass the consultant_id in the 'state' so we know who they are when they come back
    authorization_url, state = flow.authorization_url(
        access_type="offline",  # CRITICAL: This gives you the refresh token
        include_granted_scopes="true",
        state=consultant_id,
    )

    return RedirectResponse(authorization_url)


@router.get("/callback")
async def auth_callback(code: str, state: str):
    consultant_id = state

    flow = Flow.from_client_secrets_file(
        "client_secrets.json",
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        redirect_uri="https://your-api.com/auth/callback",
    )

    # Exchange the code for tokens
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Save credentials.refresh_token to Supabase for this consultant_id
    db.save_refresh_token(consultant_id, credentials.refresh_token)

    return {"message": "Calendar connected successfully!"}
