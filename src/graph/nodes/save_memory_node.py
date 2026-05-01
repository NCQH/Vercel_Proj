"""
LangGraph node: save_memory

Runs after the LLM produces its final (non-tool) response.
Persists conversation turns and refreshes the session summary.
"""

import logging

from langchain_openai import ChatOpenAI

from src.config import (
    MEMORY_SUMMARY_MODEL,
    MEMORY_SUMMARY_TURNS,
    OPENAI_API_KEY,
)
from src.graph.state import AgentState
from src.memory.memory_service import (
    refresh_session_summary_with_llm,
    save_conversation_turn,
    save_memory,
)

logger = logging.getLogger(__name__)

# Lightweight client used only for the summary LLM call
_summary_client = None


def _get_summary_client():
    global _summary_client
    if _summary_client is None:
        from openai import OpenAI
        _summary_client = OpenAI(api_key=OPENAI_API_KEY)
    return _summary_client


def save_memory_node(state: AgentState) -> dict:
    """Persist memory, conversation turn, and session summary."""

    user_id = state["user_id"]
    session_id = state["session_id"]

    # Extract user question and assistant answer from messages
    user_input = ""
    assistant_answer = ""

    for msg in state["messages"]:
        if msg.type == "human":
            user_input = msg.content
        elif msg.type == "ai" and not getattr(msg, "tool_calls", None):
            assistant_answer = msg.content or ""

    # Use the *last* user message & last assistant message
    for msg in reversed(state["messages"]):
        if msg.type == "ai" and not getattr(msg, "tool_calls", None):
            assistant_answer = msg.content or ""
            break

    for msg in reversed(state["messages"]):
        if msg.type == "human":
            user_input = msg.content
            break

    # 1. Save typed durable memory (semantic + episodic)
    saved_count = save_memory(user_id, user_input, session_id=session_id)
    logger.info("[MEMORY SAVE] saved %d items", saved_count)

    # 2. Save conversation turn
    save_conversation_turn(
        user_id,
        user_input,
        str(assistant_answer),
        session_id=session_id,
    )
    logger.info("[CONTEXT SAVE] saved 1 turn")

    # 3. Refresh session summary (uses raw OpenAI client for compatibility)
    client = _get_summary_client()
    summary = refresh_session_summary_with_llm(
        client,
        user_id,
        model=MEMORY_SUMMARY_MODEL,
        session_id=session_id,
        max_turns_for_summary=MEMORY_SUMMARY_TURNS,
    )
    logger.info("[SUMMARY SAVE] length %d", len(summary))

    # Collect sources from tool messages
    sources = list(state.get("sources", []))
    import json
    for msg in state["messages"]:
        if msg.type == "tool":
            try:
                data = json.loads(msg.content)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            src = item.get("source")
                            if src and str(src) not in sources:
                                sources.append(str(src))
            except (json.JSONDecodeError, TypeError):
                pass

    return {"sources": sources}
