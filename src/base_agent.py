"""
AI Teaching Assistant — LangGraph-powered agent.

This module provides `run_agent()` which invokes the compiled LangGraph
and returns the final assistant reply with appended sources.

The interactive CLI (`main()`) is preserved for local testing.
"""

import logging

from langchain_core.messages import HumanMessage

from src.config import LOG_LEVEL
from src.graph.builder import graph, route_after_guardrail
from src.memory.memory_service import debug_memory_recall
from src.config import MEMORY_FACT_MAX_DISTANCE, MEMORY_FACT_TOP_K

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def _build_initial_state(
    user_input: str,
    user_id: str = "default",
    session_id: str = "default",
    allowed_sources: list[str] | None = None,
    allowed_collections: list[str] | None = None,
    preferred_sources: list[str] | None = None,
) -> dict:
    return {
        "messages": [HumanMessage(content=user_input)],
        "user_id": user_id,
        "session_id": session_id,
        "sources": [],
        "allowed_sources": allowed_sources or [],
        "allowed_collections": allowed_collections or [user_id],
        "preferred_sources": preferred_sources or [],
        "memory_block": "",
        "summary_block": "",
        "route": "",
        "route_reason": "",
        "retrieved_chunks": [],
        "final_answer": "",
        "guardrail_passed": True,
        "guardrail_rejection": "",
        "is_academic": False,
    }


def run_agent(
    user_input: str,
    user_id: str = "default",
    session_id: str = "default",
    allowed_sources: list[str] | None = None,
    allowed_collections: list[str] | None = None,
    preferred_sources: list[str] | None = None,
) -> tuple[str, dict]:
    """Run the LangGraph agent and return the final answer string and state."""
    initial_state = _build_initial_state(user_input, user_id, session_id, allowed_sources, allowed_collections, preferred_sources)
    result = graph.invoke(initial_state, {"recursion_limit": 25})

    final_answer = ""
    for msg in reversed(result["messages"]):
        if msg.type == "ai" and not getattr(msg, "tool_calls", None):
            final_answer = msg.content or ""
            break

    return final_answer, result


def run_agent_events(
    user_input: str,
    user_id: str = "default",
    session_id: str = "default",
    allowed_sources: list[str] | None = None,
    allowed_collections: list[str] | None = None,
    preferred_sources: list[str] | None = None,
):
    """Yield real execution events from the LangGraph run."""
    state = _build_initial_state(user_input, user_id, session_id, allowed_sources, allowed_collections, preferred_sources)
    latest_state = state
    yield {"type": "step", "step": "Loading memory context", "node": "load_memory"}

    for event in graph.stream(state, {"recursion_limit": 25}, stream_mode="updates"):
        for node_name, update in event.items():
            if isinstance(update, dict):
                latest_state = {**latest_state, **update}

            if node_name == "load_memory":
                yield {"type": "step", "step": "Checking content safety & intent", "node": "guardrail_input"}
            elif node_name == "guardrail_input":
                route = route_after_guardrail(latest_state)
                if route == "retrieval":
                    yield {"type": "step", "step": "Searching knowledge base", "node": "retrieval"}
                elif route == "direct":
                    yield {"type": "step", "step": "Drafting response", "node": "tutor"}
                else:
                    yield {"type": "step", "step": "Saving conversation memory", "node": "save_memory"}
            elif node_name == "retrieval":
                sources = latest_state.get("sources") or []
                chunk_count = len(latest_state.get("retrieved_chunks") or [])
                yield {
                    "type": "step",
                    "step": f"Retrieved {chunk_count} relevant chunk(s) from {len(sources)} source(s)",
                    "node": "tutor",
                }
            elif node_name == "tutor":
                yield {"type": "step", "step": "Saving conversation memory", "node": "save_memory"}
            elif node_name == "save_memory":
                yield {"type": "done", "state": latest_state}
                return

    yield {"type": "done", "state": latest_state}



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
            response, state = run_agent(
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