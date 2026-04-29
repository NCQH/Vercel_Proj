"""
AI Teaching Assistant — LangGraph-powered agent.

This module provides `run_agent()` which invokes the compiled LangGraph
and returns the final assistant reply with appended sources.

The interactive CLI (`main()`) is preserved for local testing.
"""

import logging

from langchain_core.messages import HumanMessage

from src.config import LOG_LEVEL
from src.graph.builder import graph
from src.memory.memory_service import debug_memory_recall
from src.config import MEMORY_FACT_MAX_DISTANCE, MEMORY_FACT_TOP_K

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def run_agent(
    user_input: str,
    user_id: str = "default",
    session_id: str = "default",
) -> str:
    """
    Run the LangGraph agent and return the final answer string.

    Args:
        user_input:  The user's question.
        user_id:     Identifies the user for memory.
        session_id:  Groups turns within a session.

    Returns:
        The assistant's final response (with sources appended if any).
    """

    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_id": user_id,
        "session_id": session_id,
        "sources": [],
        "memory_block": "",
        "summary_block": "",
        "route": "",
        "route_reason": "",
        "retrieved_chunks": [],
        "final_answer": "",
    }

    # Invoke the compiled LangGraph (recursion_limit acts as max_turns)
    result = graph.invoke(initial_state, {"recursion_limit": 25})

    # Extract the final assistant message
    final_answer = ""
    for msg in reversed(result["messages"]):
        if msg.type == "ai" and not getattr(msg, "tool_calls", None):
            final_answer = msg.content or ""
            break

    # Append sources if the model didn't include them
    sources = result.get("sources", [])
    if sources and "sources:" not in final_answer.lower():
        source_block = "\nSources:\n" + "\n".join(f"- {s}" for s in sources)
        final_answer = final_answer.rstrip() + source_block

    return final_answer


# ------------------------------------------------------------------
# Interactive CLI (local testing)
# ------------------------------------------------------------------

def main():
    """Interactive CLI for testing the LangGraph agent."""

    user_id = input("User ID (default: default): ").strip() or "default"
    session_id = input("Session ID (default: auto): ").strip() or "cli"

    print("LangGraph Agent (type 'quit' to exit)")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        if user_input.startswith("/memory-debug"):
            debug_query = user_input.replace("/memory-debug", "", 1).strip()
            if not debug_query:
                print("\nUsage: /memory-debug <query>")
                continue

            rows = debug_memory_recall(
                user_id,
                debug_query,
                top_k=MEMORY_FACT_TOP_K,
                max_distance=MEMORY_FACT_MAX_DISTANCE,
            )
            print("\n[Memory Debug]")
            if not rows:
                print("No relevant memory found.")
                continue

            for idx, row in enumerate(rows, start=1):
                dist = row.get("distance")
                meta = row.get("metadata", {})
                print(f"{idx}. distance={dist} | type={meta.get('memory_type')} | source={meta.get('source')}")
                print(f"   text: {row.get('text')}")
            continue

        try:
            response = run_agent(
                user_input,
                user_id=user_id,
                session_id=session_id,
            )
            print(f"\nAgent: {response}")

        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()