# workflows/agents/guardian.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from utils.helpers import now_local
from utils.logger import get_logger
from workflows.prompts.guardian import GUARDRAIL_SYSTEM_PROMPT
from models.guardian import Guardian

logger = get_logger(__name__)


class GuardianAgent:
    def __init__(self):
        # low temperature 0 to assure consitency in the classification
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.base_prompt_string = GUARDRAIL_SYSTEM_PROMPT
        self.structured_llm = self.llm.with_structured_output(Guardian)

    async def check_and_route(self, history: list, active_consultant_name: str) -> str:
        """Evaluate the dynamic context and the history to take a routing decision."""
        try:
            formatted_guard = self.base_prompt_string.format(
                current_date=now_local(),
                owner_name="Financial Brokerage Firm",
                active_consultant_name=active_consultant_name,
            )

            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", formatted_guard),
                    MessagesPlaceholder(variable_name="history"),
                    (
                        "system",
                        (
                            "CRITICAL REMINDER: Do NOT reply to the user message above. Do NOT answer their questions. "
                            "Your ONLY job is to analyze the user intent using the historical context and extract slots.\n"
                            "Fill the JSON schema properties accurately:\n"
                            "- 'status': Choose exactly one option ('ALLOWED', 'REJECTED', 'ERROR').\n"
                            "- 'destination': Choose the target node ('concierge', 'book', 'rescheduler', 'onboarding').\n"
                            "- Extract 'extracted_consultant', 'extracted_date', and 'extracted_time' if they are explicitly mentioned in the last user message. Otherwise, leave them as null."
                        ),
                    ),
                ]
            )

            chain = prompt_template | self.structured_llm
            decision = await chain.ainvoke({"history": history})

            logger.info(f"Guardrail Structured Output: {decision.model_dump()}")

            return decision

        except Exception as e:
            logger.error(f"Router core failure: {e}", exc_info=True)
            return Guardian(status="ERROR", destination="concierge")
