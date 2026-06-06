# workflows/agents/concierge.py
import json
from typing import Any, Dict, Tuple

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from services.database_service import DatabaseService
from utils.helpers import now_local
from utils.logger import get_logger
from workflows.prompts.concierge import CONCIERGE_PROMPT

logger = get_logger(__name__)

db = DatabaseService()

# ------------------------------------------------------------------
# 🌟 Global Standalone Tools (Clean & Decoupled)
# ------------------------------------------------------------------


@tool
async def get_consultants_info(consultant_name: str) -> str:
    """Fetch background profile, specialties, and bio of a specific consultant by name."""
    name_query = consultant_name

    results = await db.find_consultants_by_name(name_query)
    return json.dumps(results, ensure_ascii=False)


@tool
async def set_consultant(consultant_id: str) -> str:
    """Lock in and assign a consultant to the user's active session using their unique verified ID."""
    logger.info(f"Locking in consultant with ID: {consultant_id}")

    consultant = await db.get_consultant(consultant_id)
    return consultant


# ------------------------------------------------------------------
# Concierge Agent Component
# ------------------------------------------------------------------


class ConciergeAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

        self.tools = [get_consultants_info, set_consultant]
        self.llm_with_tools = self.llm.bind_tools(self.tools, parallel_tool_calls=False)
        self.tools_map = {tool.name: tool for tool in self.tools}

    async def execute_turn(self, state: dict) -> Tuple[str, Dict[str, Any]]:
        active_c = state.get("active_consultant_name") or "None Selected"

        slots = state.get("slots") or {}

        date = slots.get("date")
        time = slots.get("time")

        if date and time:
            slots_summary = f"{date} at {time}"
        else:
            slots_summary = date or time or "None"

        formatted_system = CONCIERGE_PROMPT.format(
            today=now_local(),
            active_consultant_name=active_c,
            slots_context=slots_summary,
        )

        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", formatted_system),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        updates = {
            "active_consultant_name": state.get("active_consultant_name") or "",
            "active_consultant_id": state.get("active_consultant_id") or "",
            "next_agent": "end",
        }

        current_messages = list(state.get("messages", []))

        for _ in range(3):
            chain = prompt_template | self.llm_with_tools
            ai_msg = await chain.ainvoke({"messages": current_messages})

            if not ai_msg.tool_calls:
                return ai_msg.content, updates

            current_messages.append(ai_msg)

            for tool_call in ai_msg.tool_calls:
                tool_name = tool_call["name"]
                args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"Executing tool dynamically: {tool_name}")

                target_tool = self.tools_map.get(tool_name)

                if not target_tool:
                    content_str = (
                        f"Tool '{tool_name}' not found in agent configuration."
                    )
                    logger.error(content_str)
                else:
                    try:
                        result = await target_tool.ainvoke(args)
                        if tool_name == "set_consultant" and result:
                            consultant_dict = (
                                dict(result) if not isinstance(result, dict) else result
                            )

                            updates["active_consultant_name"] = consultant_dict.get(
                                "name", ""
                            )
                            updates["active_consultant_id"] = str(
                                consultant_dict.get("id", "")
                            )
                            logger.info(
                                f"Successfully populated updates: {updates}"
                            )  # Convertimos el resultado a string si viene como dict/objeto de la DB
                        content_str = (
                            json.dumps(result, ensure_ascii=False)
                            if isinstance(result, (dict, list))
                            else str(result)
                        )
                    except Exception as e:
                        content_str = f"Execution error on tool '{tool_name}': {str(e)}"
                        logger.error(content_str)

                current_messages.append(
                    ToolMessage(content=content_str, tool_call_id=tool_id)
                )

        return (
            "I'm having trouble organizing that right now. How else can I help you?",
            updates,
        )
