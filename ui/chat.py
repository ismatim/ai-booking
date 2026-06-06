# ui/chat.py
import os
import sqlite3
import sys
import time

import requests
import streamlit as st
from langgraph.checkpoint.sqlite import SqliteSaver

from config import get_settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


settings = get_settings()

# --- Configuration ---
FASTAPI_URL = "http://localhost:8000/webhook/twilio"
DB_PATH = os.path.join(BASE_DIR, settings.database_filename)

st.set_page_config(
    page_title="WhatsApp AI Agent Test Bench", page_icon="🤖", layout="centered"
)
st.title("🤖 WhatsApp AI Agent Test Bench")
st.write(
    "Simulate incoming WhatsApp messages and monitor LangGraph's local SQLite state."
)


# --- Helper: Clean phone number string to match Database thread_id ---
def clean_thread_id(thread_id: str) -> str:
    """Removes '+' and hidden spaces to match the FastAPI normalization logic."""
    return thread_id.replace("+", "").strip()


# --- Helper: Fetch Active Thread IDs from SQLite ---
def get_active_threads():
    threads = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
        threads = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
    except Exception:
        pass
    return threads


def get_langgraph_history(thread_id):
    messages = []
    safe_thread_id = clean_thread_id(thread_id)

    config = {"configurable": {"thread_id": safe_thread_id}}

    try:
        with SqliteSaver.from_conn_string(DB_PATH) as saver:
            checkpoint_tuple = saver.get_tuple(config)

            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                checkpoint = checkpoint_tuple.checkpoint
                channel_values = checkpoint.get("channel_values", {})
                raw_msgs = channel_values.get("messages", [])

                for msg in raw_msgs:
                    # El checkpointer native returns real objects from LangChain
                    msg_type = getattr(msg, "type", "")
                    content = getattr(msg, "content", "")

                    if content and isinstance(content, str):
                        role = "user" if msg_type == "human" else "assistant"
                        messages.append({"role": role, "content": content})

    except Exception as e:
        st.sidebar.error(f"🔴 Error processing native history: {e}")

    return messages


# --- 📱 Sidebar: Multi-User Simulation Workspace ---
st.sidebar.header("📱 Multi-User Simulation")

existing_threads = get_active_threads()
base_mock_threads = [
    "541112345678",
    "14155552671",
]  # Without '+'
thread_options = list(set(existing_threads + base_mock_threads)) + [
    "➕ Add New Number..."
]

selected_thread_option = st.sidebar.selectbox(
    "Active WhatsApp Accounts", options=thread_options, index=0
)

if selected_thread_option == "➕ Add New Number...":
    phone_number = st.sidebar.text_input(
        "Enter New Phone Number (digits only)", value="541199999999"
    )
else:
    phone_number = selected_thread_option

user_name = st.sidebar.text_input("WhatsApp Profile Name", value="Juan Perez")

st.sidebar.markdown("---")

# --- Clear session logic ---
if st.sidebar.button("🗑️ Clear Memory for This Thread"):
    safe_thread_id = clean_thread_id(phone_number)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. remove table checkpoints
        try:
            cursor.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?", (safe_thread_id,)
            )
        except sqlite3.OperationalError:
            pass  # Se salta si la tabla no existe temporalmente

        # 2. remove checkpoint_writes
        try:
            cursor.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = ?", (safe_thread_id,)
            )
        except sqlite3.OperationalError:
            pass

        # 3. remove checkpoint_blobs
        try:
            cursor.execute(
                "DELETE FROM checkpoint_blobs WHERE thread_id = ?", (safe_thread_id,)
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()

        st.sidebar.success(f"Memory wiped clean for {safe_thread_id}!")
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.sidebar.error(f"Could not clear memory: {e}")
# --- Main Window: Render Active Conversation ---
st.subheader(f"💬 Live Chat Thread: {phone_number}")
chat_history = get_langgraph_history(phone_number)

if not chat_history:
    st.info(
        "No message history found for this phone number. Type a message below to start the conversation!"
    )

for msg in chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- Chat Input & Webhook Trigger ---
if user_input := st.chat_input("Type your message here..."):
    with st.chat_message("user"):
        st.write(user_input)

    payload = {
        "From": f"whatsapp:{clean_thread_id(phone_number)}",
        "Body": user_input,
        "ProfileName": user_name,
    }

    with st.spinner("Agent is thinking..."):
        try:
            response = requests.post(FASTAPI_URL, data=payload)
            if response.status_code == 200:
                with st.empty():
                    for _ in range(25):
                        time.sleep(0.3)
                        history = get_langgraph_history(phone_number)

                        # Si el último mensaje en la base de datos ya es del asistente,
                        # significa que LangGraph terminó de escribir y podemos refrescar
                        if history and history[-1]["role"] == "assistant":
                            break

                st.rerun()
            else:
                st.error(f"Webhook error: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error(
                "Could not connect to FastAPI server. Make sure it is running on port 8000!"
            )
