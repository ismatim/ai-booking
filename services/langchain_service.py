# services/langchain_service.py
import os
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from workflows.agenda import AgendaWorkflow
from config import get_settings
from typing import Optional

settings = get_settings()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ABSOLUTE_PATH = os.path.join(BASE_DIR, "app.db")


class LangChainService:
    def __init__(self):
        self.workflow = AgendaWorkflow()

    async def process_message(
        self,
        user_message: str,
        thread_id: str,
        sender_name: str,
        user_context: Optional[dict] = None,
    ):
        async with AsyncSqliteSaver.from_conn_string(DB_ABSOLUTE_PATH) as memory:
            compiled_graph = self.workflow.compile(checkpointer=memory)
            config = {"configurable": {"thread_id": thread_id}}

            initial_state = {
                "messages": [("user", user_message)],
                "next_agent": "guardian",
                "user_context": user_context or {},
                "user_name": sender_name,
                "user_message": user_message,
                "user_phone": thread_id,
            }

            graph_output = await compiled_graph.ainvoke(initial_state, config=config)

            return graph_output["messages"][-1].content
