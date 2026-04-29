"""
LangGraph node: retrieval

Calls retrieval agent and stores chunks + sources in state.
"""

from __future__ import annotations

from src.agents.retrieval_agent import run as run_retrieval
from src.graph.state import AgentState


def retrieval_node(state: AgentState) -> dict:
    question = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            question = msg.content
            break

    result = run_retrieval(question, mode="hybrid", top_k=5)
    return {
        "retrieved_chunks": result.get("chunks", []),
        "sources": result.get("sources", []),
    }