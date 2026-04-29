"""
LangGraph node: load_memory

Runs at the start of each invocation.  Fetches long-term facts and
session summary from the memory service and injects them into the
system prompt that sits at `messages[0]`.
"""

import logging

from langchain_core.messages import SystemMessage

from src.config import (
    MEMORY_CONTEXT_TURNS,
    MEMORY_FACT_MAX_DISTANCE,
    MEMORY_FACT_TOP_K,
)
from src.graph.state import AgentState
from src.memory.memory_service import (
    load_context_messages,
    load_memory,
    load_session_context_summary,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an AI Teaching Assistant.

You MUST use the tool `search_course_material` before answering any question related to:
- lectures
- course content
- documents
- definitions in the syllabus

Tool usage rules:
- Always call tool first if question is academic/content-based
- If tool returns multiple chunks, synthesize them
- If tool returns empty, say you don't know

You are not allowed to answer from memory for course-related questions.

Output format:
Answer: ...
Sources:
- source1
- source2
"""


def load_memory_node(state: AgentState) -> dict:
    """Fetch memory + session summary and prepend a system message."""

    user_id = state["user_id"]
    # Extract user's latest message text for memory query
    user_input = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            user_input = msg.content
            break

    # --- Long-term memory ---
    memory = load_memory(
        user_id,
        user_input,
        top_k=MEMORY_FACT_TOP_K,
        max_distance=MEMORY_FACT_MAX_DISTANCE,
    ) or []

    memory_block = ""
    if memory:
        memory_block = "\nUser Memory:\n" + "\n".join(f"- {m}" for m in memory)

    # --- Session summary ---
    session_summary = load_session_context_summary(user_id)
    summary_block = ""
    if session_summary:
        summary_block = f"\nSession Summary:\n{session_summary}"

    # --- Context messages (recent conversation turns) ---
    context_messages = load_context_messages(
        user_id,
        max_turns=MEMORY_CONTEXT_TURNS,
    ) or []

    logger.info("[MEMORY] loaded %d facts, %d context turns", len(memory), len(context_messages))

    # Build final system prompt
    system_content = SYSTEM_PROMPT + f"\n{memory_block}{summary_block}"
    system_msg = SystemMessage(content=system_content)

    # Rebuild messages: system → context history → current user message
    from langchain_core.messages import HumanMessage, AIMessage

    rebuilt: list = [system_msg]
    for cm in context_messages:
        role = cm.get("role", "user")
        content = cm.get("content", "")
        if role == "user":
            rebuilt.append(HumanMessage(content=content))
        elif role == "assistant":
            rebuilt.append(AIMessage(content=content))

    # Append the current user message (last human message from state)
    if user_input:
        rebuilt.append(HumanMessage(content=user_input))

    return {
        "messages": rebuilt,
        "memory_block": memory_block,
        "summary_block": summary_block,
        "sources": [],
    }
