import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.langchain_service import LangChainService
from utils.timezone import format_human_readable_date
from langchain_core.messages import HumanMessage, AIMessage
from config import get_settings


from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langsmith_tracing else "false"
os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"


@pytest.mark.asyncio
async def test_reschedule_intent_tracing():
    # 1. Setup the REAL service
    ai_svc = LangChainService()

    # 2. Mock the inputs
    mock_history = []  # Fresh conversation
    mock_context = {
        "current_time": "2026-04-17T10:00:00Z",
        "timezone": "America/Argentina/Buenos_Aires",
        "active_consultant": {"name": "Sofia", "id": "sofia-123"},
        "reschedule_id": "booking-999",
    }

    # Use your helper to format the 'today' string
    mock_context["today"] = format_human_readable_date(
        mock_context["current_time"], mock_context["timezone"]
    )

    user_message = "I need to move my meeting with Sofia to next Friday."

    # 3. Execute the Chain
    # We add a tag so we can find this specific test run in LangSmith
    result = await ai_svc.chain.ainvoke(
        {"user_message": user_message, "history": mock_history, **mock_context},
        config={"tags": ["pytest-integration-test"]},
    )

    logger.info(f"LangChain Chain result: {result}")
    # 4. Assertions: Did the "Chain" link correctly?
    assert isinstance(result, dict), "Result should be a parsed JSON/Dict"
    assert "action" in result
    assert "raw_response" in result

    # Specifically check if it respected the reschedule_id in the context
    if result["action"] == "reschedule_booking":
        assert result["data"]["booking_id"] == "booking-999"
        print("\n✅ AI successfully linked the context ID!")
    else:
        print(f"\nℹ️ AI chose action: {result['action']}. Check LangSmith to see why.")


@pytest.mark.asyncio
async def test_multi_turn_reschedule_flow():
    ai_svc = LangChainService()

    # 1. Setup Base Context
    current_time = "2026-04-17T11:00:00Z"
    tz = "America/Argentina/Buenos_Aires"

    # 2. Simulate the History (The "Back and Forth")
    # This represents the messages already stored in your DB
    history = [
        HumanMessage(content="Hi, I'm looking for a financial advisor."),
        AIMessage(
            content="Hello! I can certainly help with that. We have Sofia (Investment Specialist) and Marcos (Tax Consultant). Who would you like to speak with?"
        ),
        HumanMessage(
            content="Sofia sounds great. Also, I have an existing appointment I need to change."
        ),
    ]

    # 3. The Current turn context
    # Note: We simulate that the system has already identified the booking to change
    user_context = {
        "today": format_human_readable_date(current_time, tz),
        "timezone": tz,
        "active_consultant": {
            "name": "Sofia",
            "id": "sofia-123",
            "specialty": "Investments",
        },
        "reschedule_id": "BK-5555",  # The "Sticky Note" from our previous work
    }

    # 4. The Final User Message (The "Punchline")
    user_message = (
        "Actually, can we just move that BK-5555 appointment to next Tuesday at 2 PM?"
    )

    # 5. Run the Chain
    result = await ai_svc.chain.ainvoke(
        {"user_message": user_message, "history": history, **user_context},
        config={"tags": ["multi-turn-test", "reschedule-flow"]},
    )

    # 6. Verify the "Brain" worked
    print(f"\nFinal AI Response: {result['raw_response']}")
    print(f"Action Taken: {result['action']}")
    print(f"Data: {result['data']}")

    assert result["action"] == "reschedule_booking"
    assert result["data"]["booking_id"] == "BK-5555"
    # Next Tuesday from April 17 (Friday) should be April 21
    assert "2026-04-21" in result["data"]["new_start_time"]
