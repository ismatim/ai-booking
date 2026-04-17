import uuid
import psycopg
from langchain_postgres import PostgresChatMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser

from config import get_settings
from utils.logger import get_logger

from prompts.concierge import (
    BASE_SYSTEM_PROMPT,
    JSON_FORMAT_INSTRUCTIONS,
    ACTION_DEFINITIONS,
)

settings = get_settings()
logger = get_logger(__name__)


class LangChainService:
    def __init__(self):
        # Initialize the Model
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-lite-latest",
            temperature=0.2,
            google_api_key=settings.gemini_api_key,
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", BASE_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{user_message}"),
            ]
        ).partial(
            # Inject the problematic JSON braces as STATIC strings
            # This prevents LangChain from trying to parse them as variables
            format_instructions=JSON_FORMAT_INSTRUCTIONS,
            action_definitions=ACTION_DEFINITIONS,
        )

        self.parser = JsonOutputParser()
        # Create the Chain
        self.chain = self.prompt | self.llm | self.parser

    async def process_message(
        self, user_phone: str, user_message: str, user_context: dict
    ):
        # uuid5 uses a namespace (we'll use DNS) to hash your phone number into a valid UUID
        session_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_phone))

        # Connection string must be the 'postgresql://' URI from Supabase
        with psycopg.connect(settings.supabase_conn, prepare_threshold=None) as conn:
            # 1. Initialize History (Automatic Load)
            history = PostgresChatMessageHistory(
                "messages", session_uuid, sync_connection=conn
            )
            # 2. Build Inputs
            inputs = {
                "user_message": user_message,
                "history": history.messages,  # Loads previous turns automatically
                "today": user_context.get("today") or user_context.get("current_time"),
                "timezone": user_context.get("timezone", "UTC"),
                "active_consultant": user_context.get("active_consultant"),
                "reschedule_id": user_context.get("reschedule_id"),
            }

            # 3. Call Gemini
            ai_result = await self.chain.ainvoke(inputs)

            # 4. Automatic Save (This populates your new columns!)
            history.add_user_message(user_message)
            history.add_ai_message(ai_result.get("raw_response", ""))

            return ai_result
