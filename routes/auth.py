from google_auth_oauthlib.flow import Flow
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from database import get_db

from config import get_settings

from utils.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()
db = get_db()
router = APIRouter(prefix="/auth", tags=["Bookings"])


def create_flow(redirect_uri: str):
    return Flow.from_client_secrets_file(
        "client_secrets.json",
        scopes=["https://www.googleapis.com/auth/calendar.events"],
        redirect_uri=redirect_uri,
    )


@router.get("/google")
async def auth_google(request: Request, consultant_id: str):
    flow = Flow.from_client_secrets_file(
        "client_secrets.json",
        scopes=["https://www.googleapis.com/auth/calendar.events"],
        redirect_uri=settings.google_callback_url,
    )

    # We pass the consultant_id in the 'state' so we know who they are when they come back
    authorization_url, _ = flow.authorization_url(
        access_type="offline",  # CRITICAL: This gives you the refresh token
        include_granted_scopes="false",
        state=consultant_id,
        autogenerate_code_verifier=True,  # This is needed for PKCE flow
        prompt="consent",  # TODO: force to ask for consent, REMOVE later.
    )

    request.session["code_verifier"] = flow.code_verifier

    return RedirectResponse(authorization_url)


@router.get("/callback")
async def auth_callback(request: Request, code: str, state: str):
    consultant_id = state
    code_verifier = request.session.get("code_verifier")

    if not code_verifier:
        return {"error": "Session expired or code verifier missing"}

    flow = create_flow(settings.google_callback_url)

    # Exchange the code for tokens
    flow.code_verifier = code_verifier

    try:
        flow.fetch_token(code=code, code_verifier=code_verifier)
    except Exception as e:
        logger.error(f"Error fetching token: {e}")
        return {"error": "Failed to fetch token"}

    credentials = flow.credentials

    # Save credentials.refresh_token to Supabase for this consultant_id
    logger.info(
        f"Saving refresh token for consultant_id: {consultant_id}, refresh_token: {credentials.refresh_token}"
    )
    db.save_refresh_token(consultant_id, credentials.refresh_token)

    return {
        "message": "Calendar connected successfully!",
        "consultant_id": consultant_id,
    }


@router.get("/test-auth")
async def start_test_auth():
    # Use a real user ID from your Supabase 'users' table
    test_consultant_id = "42694d00-e6a0-4f17-99db-f15bd80b2f60"

    # Redirect the browser to your /auth/google route
    return RedirectResponse(f"/auth/google?consultant_id={test_consultant_id}")
