import os
import sys
from langsmith import Client
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Get the directory 2 levels up
root_dir = Path(__file__).resolve().parents[1]

# Add it to the path
sys.path.append(str(root_dir))

from config import get_settings

from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langsmith_tracing else "false"
os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"


def get_today_usage(project_name="ai-booking"):
    client = Client()

    # Define "Today" (Start of the day in UTC)
    start_of_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Fetch runs from today
    runs = client.list_runs(
        project_name=project_name,
        start_time=start_of_day,
        run_type="llm",  # Only count LLM calls
    )

    total_tokens = 0
    request_count = 0

    for run in runs:
        request_count += 1
        # LangChain stores usage in the 'total_tokens' metadata field
        if run.total_tokens:
            total_tokens += run.total_tokens

    return request_count, total_tokens


# --- Execution ---
requests, tokens = get_today_usage()

# Gemini Free Tier (AI Studio) limits in 2026
DAILY_LIMIT = 1000
remaining = DAILY_LIMIT - requests

print(f"📊 --- Today's Usage for {datetime.now().date()} ---")
print(f"✅ Requests Made: {requests}")
print(f"⏳ Requests Remaining (est): {max(0, remaining)}")
print(f"🔥 Total Tokens Burned: {tokens:,}")

if remaining < 100:
    print("⚠️ WARNING: You are almost out of free requests!")
