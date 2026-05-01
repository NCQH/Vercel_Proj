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
    MEMORY_EPISODIC_TOP_K,
    MEMORY_LONG_TERM_TOP_K,
    MEMORY_SEMANTIC_TOP_K,
)
from src.graph.state import AgentState
from src.memory.memory_service import (
    load_episodic_memory,
    load_long_term_memory,
    load_semantic_memory,
    load_session_context_summary,
    load_short_term_memory,
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
    """Fetch typed memory layers and prepend a memory-enriched system message."""

    user_id = state["user_id"]
    session_id = state.get("session_id", "default")

    user_input = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            user_input = msg.content
            break

    semantic_mem = load_semantic_memory(
        user_id,
        user_input,
        top_k=MEMORY_SEMANTIC_TOP_K,
        max_distance=MEMORY_FACT_MAX_DISTANCE,
    ) or []

    long_term_mem = load_long_term_memory(
        user_id,
        user_input,
        top_k=MEMORY_LONG_TERM_TOP_K,
        max_distance=MEMORY_FACT_MAX_DISTANCE,
    ) or []

    episodic_mem = load_episodic_memory(
        user_id,
        user_input,
        session_id=session_id,
        top_k=MEMORY_EPISODIC_TOP_K,
        max_distance=MEMORY_FACT_MAX_DISTANCE,
    ) or []

    session_summary = load_session_context_summary(user_id)
    short_term_messages = load_short_term_memory(
        user_id,
        session_id=session_id,
        max_turns=MEMORY_CONTEXT_TURNS,
    ) or []

    semantic_block = ""
    if semantic_mem:
        semantic_block = "\nSemantic Memory (User Profile):\n" + "\n".join(f"- {m}" for m in semantic_mem)

    long_term_block = ""
    if long_term_mem:
        long_term_block = "\nLong-term Memory:\n" + "\n".join(f"- {m}" for m in long_term_mem)

    episodic_block = ""
    if episodic_mem:
        episodic_block = "\nEpisodic Memory (Relevant Sessions):\n" + "\n".join(f"- {m}" for m in episodic_mem)

    summary_block = ""
    if session_summary:
        summary_block = f"\nSession Summary:\n{session_summary}"

    logger.info(
        "[MEMORY] semantic=%d long_term=%d episodic=%d short_turns=%d",
        len(semantic_mem),
        len(long_term_mem),
        len(episodic_mem),
        len(short_term_messages),
    )

    system_content = SYSTEM_PROMPT + f"\n{semantic_block}{long_term_block}{episodic_block}{summary_block}"
    system_msg = SystemMessage(content=system_content)

    from langchain_core.messages import HumanMessage, AIMessage

    rebuilt: list = [system_msg]
    for cm in short_term_messages:
        role = cm.get("role", "user")
        content = cm.get("content", "")
        if role == "user":
            rebuilt.append(HumanMessage(content=content))
        elif role == "assistant":
            rebuilt.append(AIMessage(content=content))

    if user_input:
        rebuilt.append(HumanMessage(content=user_input))

    combined_memory_block = "\n".join(
        [b for b in [semantic_block, long_term_block, episodic_block] if b.strip()]
    )

    return {
        "messages": rebuilt,
        "memory_block": combined_memory_block,
        "summary_block": summary_block,
        "sources": [],
    }
