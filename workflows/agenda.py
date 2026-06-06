# workflows/agenda.py
from typing import Dict, Annotated, Literal, Any, Optional
from typing_extensions import TypedDict
from langgraph.types import Command
from pydantic import EmailStr, UUID4
from pydantic_extra_types.phone_numbers import PhoneNumber
from datetime import datetime
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from workflows.agents.guardian import GuardianAgent
from workflows.agents.concierge import ConciergeAgent
from workflows.agents.booking import BookingAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class AgendaState(TypedDict):
    active_consultant_name: str
    active_consultant_id: str  # O UUID4, según prefieras en tu DB

    # user's messages
    latest_user_input: str
    messages: Annotated[list, add_messages]

    # Guardian slots requested
    slots: Optional[Dict[str, Any]]  # O tu modelo ExtractedSlots

    # flow & infrastructure
    current_time: datetime
    discovery_mode: bool
    has_booking: bool
    language: str
    reschedule_id: UUID4
    user_id: UUID4
    user_name: str
    user_phone: PhoneNumber
    next_agent: str
    user_context: Dict
    timezone: str


class AgendaWorkflow:
    def __init__(self):
        self.guardian = GuardianAgent()
        self.concierge = ConciergeAgent()
        self.booking = BookingAgent()
        self.builder = StateGraph(AgendaState)
        self._build_workflow()

    def _build_workflow(self):
        # 1. Register all work nodes
        self.builder.add_node(
            "guardian",
            self._guard_and_distribute,
            subgraphs=["concierge", "book", "rescheduler"],
        )
        self.builder.add_node("concierge", self._process_concierge)
        self.builder.add_node("book", self._process_booking)
        self.builder.add_node("rescheduler", self._process_rescheduling)

        self.builder.add_edge(START, "guardian")

        self.builder.add_edge("concierge", END)
        self.builder.add_edge("book", END)
        self.builder.add_edge("rescheduler", END)

    # ------------------------------------------------------------------
    # The Orchestration Hub
    # -----------------------------------------------------------------
    async def _guard_and_distribute(
        self, state: AgendaState
    ) -> Command[Literal["concierge", "book", "rescheduler", "__end__"]]:
        """Intercepts inbound payloads and acts as the main distributor."""

        active_c = state.get("active_consultant_name") or "None Selected"

        guardian = await self.guardian.check_and_route(
            history=state["messages"], active_consultant_name=active_c
        )
        logger.info(f"Central Distributor Decision: {guardian.status}")

        if guardian.status == "ERROR":
            logger.error(
                "Guardrail execution aborted due to upstream API timeout/drop."
            )
            return Command(
                goto=END,
                update={
                    "messages": [
                        (
                            "assistant",
                            "I'm sorry, I ran into a minor connection issue with my systems. Could you please repeat your last message?",
                        )
                    ]
                },
            )

        if guardian.status == "REJECTED":
            logger.warning("Guardrail rejected message scope.")
            return Command(
                goto=END,
                update={
                    "messages": [
                        (
                            "assistant",
                            "This question isn't related to our booking system.",
                        )
                    ]
                },
            )
        state_updates = {}
        target_node = guardian.destination.lower()
        if guardian.status == "ALLOWED":
            if guardian.extracted_consultant:
                state_updates["extracted_consultant"] = guardian.extracted_consultant

            if guardian.extracted_date or guardian.extracted_time:
                state_updates["slots"] = {
                    "date": guardian.extracted_date,
                    "time": guardian.extracted_time,
                }

        if target_node == "book" and not state.get("active_consultant_id"):
            logger.warning(
                "Guardrail suggested BOOK, but active_consultant_id is empty. Overriding to CONCIERGE."
            )
            target_node = "concierge"

        # These are valid nodes.
        if target_node in ("concierge", "book", "rescheduler"):
            logger.info(f"Routing execution flow straight to spoke: {target_node}")
            return Command(
                goto=target_node, update=state_updates if state_updates else None
            )

        return Command(goto="concierge")

    # ------------------------------------------------------------------
    # Spoke Operational Nodes
    # ------------------------------------------------------------------

    async def _process_concierge(self, state: AgendaState) -> Dict[str, Any]:
        """Handles general consulting questions, internal tool loops, and intent routing."""
        logger.info("Executing Live Concierge Agent Spoke...")

        # 1. Ejecutamos el agente para resolver herramientas (get_info, set_consultant) internamente
        ai_reply, state_updates = await self.concierge.execute_turn(state=state)
        logger.info(f"Concierge Agent reply: {ai_reply}")
        logger.info(f"Concierge Agent state updates: {state_updates}")

        # Return the complete payload  atomically to AgendaState
        return {
            **state_updates,
            # Returning a tuple, the reducer 'add_messages'
            # add the response to the history without deleteting previous messages
            "messages": [("assistant", ai_reply)],
        }

    async def _process_booking(self, state: AgendaState) -> Dict[str, Any]:
        """Handles calendar lookups, slot selection validation, and booking commits."""
        logger.info("Executing Live Booking Agent Spoke...")

        # Invoke our isolated execution cycle
        ai_reply, state_updates = await self.booking.execute_turn(state=state)

        # Atomic commit right back to LangGraph's engine state schema
        return {
            "has_booking": state_updates["has_booking"],
            "next_agent": state_updates["next_agent"],
            "messages": [("assistant", ai_reply)],
        }

    async def _process_rescheduling(self, state: AgendaState) -> Dict[str, Any]:
        """Handles appointment updates or cancellations."""
        reply = "I can certainly help you change or cancel your existing session. Let me find your record."
        return {"messages": [("assistant", reply)]}

    def compile(self, checkpointer=None):
        return self.builder.compile(
            checkpointer=checkpointer
        )  # Action Dispatchers & Handlers
