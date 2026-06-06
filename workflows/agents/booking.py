# workflows/agents/booking.py
import asyncio
from datetime import datetime, timedelta
import json
from typing import Any, Dict, Tuple

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from models.booking import CreateBookingInput
from services.booking_service import BookingService
from services.database_service import DatabaseService
from utils.helpers import now_local
from utils.helpers import parse_time_string
from utils.logger import get_logger
from workflows.prompts.booking import BOOKING_PROMPT


logger = get_logger(__name__)


db = DatabaseService()

# ------------------------------------------------------------------
# Booking Agent Core Engine
# ------------------------------------------------------------------


class BookingAgent:
    def __init__(self):

        # 0.5 temp for high precision logic
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
        self.tools = [
            StructuredTool.from_function(
                name="check_availability",
                func=self.check_availability,
                description="Check open and available time slots for a specific consultant on a given date or weekday string.",
            ),
            StructuredTool.from_function(
                name="create_booking",
                func=self.create_booking,
                description="Commit and save a new finalized appointment slot into the company reservation database.",
                args_schema=CreateBookingInput,
            ),
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.booking_service = BookingService()

    async def check_availability(self, consultant_id: str, date: str) -> str:
        """
        Check real-time slot availability for a specific consultant by querying Google Calendar via BookingService.

        Args:
        consultant_id: The unique identifier/UUID of the consultant.
        date: The target date in STRICT 'YYYY-MM-DD' ISO format.
              CRITICAL: You must mathematically compute this string based on
              today's date provided in the context. Never output text like 'June 3rd',
              'tomorrow', or 'Friday'. Convert them to 'YYYY-MM-DD' before calling this tool.
        """
        logger.info(
            f"Tool check_availability invoked with: id={consultant_id}, date_or_day={date}"
        )

        clean_consultant_id = None
        if consultant_id and str(consultant_id).lower() not in ["none", "", "null"]:
            clean_consultant_id = str(consultant_id).strip()

        target_date = None
        try:
            target_date = datetime.fromisoformat(date.strip()).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        except ValueError:
            logger.warning(
                f"LLM failed to output strict ISO format for: '{date}'. Falling back to today."
            )
            target_date = now_local().replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            available_slots = await self.booking_service.get_available_slots(
                date=target_date,
                consultant_id=clean_consultant_id,
                slot_duration_minutes=60,
            )

            return json.dumps(
                {
                    "requested_date": date,
                    "parsed_date": target_date.strftime("%Y-%m-%d"),
                    "available_slots": available_slots,
                },
                default=str,
                ensure_ascii=False,
            )

        except Exception as e:
            logger.error(f"Error querying BookingService: {e}", exc_info=True)
            return json.dumps(
                {"error": "Failed to fetch active real-time availability."}
            )

    async def create_booking(
        self,
        consultant_id: str,
        date: str,
        time_slot: str,
        client_name: str,
        user_phone_number: str,
    ) -> str:
        try:
            target_date = datetime.strptime(date.strip(), "%Y-%m-%d").date()

            if "-" in time_slot:
                start_str, _ = time_slot.split("-", 1)
            else:
                start_str = time_slot

            start_time_parsed = parse_time_string(start_str)
            start_datetime = datetime.combine(target_date, start_time_parsed)
            end_datetime = start_datetime + timedelta(hours=1)

            booking_record = await self.booking_service.create_booking(
                user_phone_number=user_phone_number,
                consultant_id=consultant_id,
                start_time=start_datetime,
                end_time=end_datetime,
                notes=f"WhatsApp Booking for {client_name}",
            )

            return json.dumps(
                {
                    "status": "SUCCESS",
                    "booking_id": str(booking_record.get("id", "BK-2026")),
                    "message": f"Appointment successfully scheduled with ID {booking_record.get('id')}",
                },
                ensure_ascii=False,
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to execute lifecycle booking write: {str(e)}", exc_info=True
            )
            return json.dumps(
                {
                    "status": "ERROR",
                    "message": f"The reservation could not be completed: {str(e)}",
                },
                ensure_ascii=False,
            )

    async def execute_turn(self, state: dict) -> Tuple[str, Dict[str, Any]]:
        try:
            logger.info("Booking internal engine: Setting up execution frame...")

            local_dt = now_local()

            friendly_today = f"{local_dt.strftime('%A, %B %d, %Y')} (ISO: {local_dt.strftime('%Y-%m-%d')})"
            formatted_system = BOOKING_PROMPT.format(
                today=friendly_today,
                active_consultant_name=state.get("active_consultant_name")
                or "None Selected",
                active_consultant_id=state.get("active_consultant_id") or "None",
                user_name=state.get("user_name") or "Client",
            )

            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", formatted_system),
                    MessagesPlaceholder(
                        variable_name="chat_history"
                    ),  # Avoids namespace collision
                ]
            )

            # Local modifications tracker
            updates = {
                "has_booking": state.get("has_booking", False),
                "next_agent": "end",  # Remains 'end' to gracefully park the graph at every WhatsApp exchange
            }

            current_messages = list(state.get("messages", []))
            chain = prompt_template | self.llm_with_tools

            for i in range(3):
                logger.info(f"Booking LLM execution loop counter: {i + 1}")
                ai_msg = await chain.ainvoke({"chat_history": current_messages})

                if not ai_msg.tool_calls:
                    return ai_msg.content, updates

                current_messages.append(ai_msg)
                logger.info(
                    f"🔍 EXTRACTING STATE FOR TOOL. Current state keys: {list(state.keys())}"
                )
                logger.info(f"🔍 Content of state: {state}")

                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call["name"]
                    args = tool_call["args"]
                    tool_id = tool_call["id"]

                    if tool_name == "check_availability":
                        result = await self.check_availability(**args)

                    elif tool_name == "create_booking":
                        if "client_name" not in args:
                            args["client_name"] = state.get("user_name", "Client")
                        if "consultant_id" not in args:
                            args["consultant_id"] = state.get(
                                "active_consultant_id", ""
                            )
                        args["user_phone_number"] = state.get("user_phone", "-")

                        result = await self.create_booking(**args)

                        if "SUCCESS" in result:
                            updates["has_booking"] = True
                    else:
                        result = "Tool execution failure: Unknown target signature."

                    current_messages.append(
                        ToolMessage(content=result, tool_call_id=tool_id)
                    )
            return (
                "I am processing your schedule details now. What time would suit you best?",
                updates,
            )

        except Exception as e:
            logger.error(
                f"💥 CRITICAL ERROR inside BookingAgent loop: {e}", exc_info=True
            )
            return (
                "I ran into an issue accessing our reservation calendar. Let's try that step again.",
                updates,
            )
