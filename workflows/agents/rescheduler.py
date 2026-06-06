# workflows/agents/rescheduling.py
import json
from typing import Dict, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from workflows.prompts.rescheduling import RESCHEDULER_PROMPT
from utils.helpers import now_local
from utils.logger import get_logger

logger = get_logger(__name__)

# Mock Active Database for appointments
MOCK_BOOKINGS_DB = {
    "BK-2026-9874": {
        "booking_id": "BK-2026-9874",
        "client_name": "Juan Perez",
        "consultant_name": "Ana Martínez",
        "date": "2026-05-29",
        "time": "09:00 AM",
    }
}

# ------------------------------------------------------------------
# 🔄 Global Standalone Rescheduling Tools
# ------------------------------------------------------------------


@tool
def get_active_bookings(client_name: str) -> str:
    """Look up current active appointment records inside the database using the client's full name."""
    found = []
    for bid, details in MOCK_BOOKINGS_DB.items():
        if client_name.lower() in details["client_name"].lower():
            found.append(details)

    if found:
        return json.dumps({"status": "FOUND", "records": found})
    return json.dumps(
        {
            "status": "NOT_FOUND",
            "message": f"No active appointments found for client '{client_name}'.",
        }
    )


@tool
def modify_booking(booking_id: str, new_date: str, new_time: str) -> str:
    """Update and rewrite an existing appointment record with a new date and time slot string."""
    if booking_id in MOCK_BOOKINGS_DB:
        MOCK_BOOKINGS_DB[booking_id]["date"] = new_date
        MOCK_BOOKINGS_DB[booking_id]["time"] = new_time
        logger.info(
            f"🔄 Database updated: {booking_id} shifted to {new_date} at {new_time}"
        )
        return json.dumps(
            {
                "status": "SUCCESS",
                "message": f"Record {booking_id} successfully changed.",
            }
        )
    return json.dumps(
        {"status": "ERROR", "message": "Invalid Booking ID target reference."}
    )


@tool
def cancel_booking(booking_id: str) -> str:
    """Completely remove and delete a verified appointment record from the booking engine database."""
    if booking_id in MOCK_BOOKINGS_DB:
        logger.info(f"🗑️ Database purge: Removing record {booking_id}")
        del MOCK_BOOKINGS_DB[booking_id]
        return json.dumps(
            {
                "status": "SUCCESS",
                "message": f"Appointment {booking_id} has been fully canceled.",
            }
        )
    return json.dumps(
        {"status": "ERROR", "message": "Record target not found. Cancellation failed."}
    )


# ------------------------------------------------------------------
# Reschedule Agent Core Engine
# ------------------------------------------------------------------


class RescheduleAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", temperature=0.0
        )  # High compliance configuration
        self.tools = [get_active_bookings, modify_booking, cancel_booking]
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    async def execute_turn(self, state: dict) -> Tuple[str, Dict[str, Any]]:
        try:
            logger.info(
                "Reschedule internal engine: Bootstrapping environment contexts..."
            )

            formatted_system = RESCHEDULER_PROMPT.format(
                today=now_local(),
                active_consultant=state.get("active_consultant") or "None Selected",
                user_name=state.get("user_name") or "Client",
            )

            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", formatted_system),
                    MessagesPlaceholder(variable_name="chat_history"),
                ]
            )

            updates = {
                "has_booking": state.get("has_booking", True),
                "next_agent": "end",
            }

            current_messages = list(state.get("messages", []))
            chain = prompt_template | self.llm_with_tools

            for i in range(3):
                logger.info(f"Reschedule LLM processing chain step: {i + 1}")
                ai_msg = await chain.ainvoke({"chat_history": current_messages})

                if not ai_msg.tool_calls:
                    return ai_msg.content, updates

                current_messages.append(ai_msg)

                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call["name"]
                    args = tool_call["args"]
                    tool_id = tool_call["id"]

                    logger.info(
                        f"Reschedule Engine: Invoking active tool -> {tool_name}"
                    )

                    if tool_name == "get_active_bookings":
                        if "client_name" not in args:
                            args["client_name"] = state.get("user_name", "Client")
                        result = get_active_bookings.invoke(args)

                    elif tool_name == "modify_booking":
                        result = modify_booking.invoke(args)

                    elif tool_name == "cancel_booking":
                        result = cancel_booking.invoke(args)
                        if '"SUCCESS"' in result or "SUCCESS" in result:
                            updates["has_booking"] = (
                                False  # Flag session state that booking is gone
                            )
                    else:
                        result = "Target tool specification missing from routing table."

                    from langchain_core.messages import ToolMessage

                    current_messages.append(
                        ToolMessage(content=result, tool_call_id=tool_id)
                    )

            return (
                "I am verifying your appointment details now. Could you confirm the changes you'd like to make?",
                updates,
            )

        except Exception as e:
            logger.error(
                f"💥 CRITICAL ERRROR inside RescheduleAgent core context: {e}",
                exc_info=True,
            )
            return (
                "I faced a brief hitch looking up your files. Could you restate your schedule request?",
                updates,
            )
