"""
LangGraph node: tutor

Creates final assistant message from retrieved context.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from src.agents.tutor_agent import generate_answer
from src.graph.state import AgentState


def tutor_node(state: AgentState) -> dict:
    question = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            question = msg.content
            break

    chunks = state.get("retrieved_chunks", [])
    result = generate_answer(question, chunks)
    answer = result.get("answer", "")
    used_sources = result.get("used_sources", [])
    return {
        "messages": [AIMessage(content=answer)],
        "final_answer": answer,
        "sources": used_sources,
    }
