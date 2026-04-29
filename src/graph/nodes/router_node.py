"""
LangGraph node: router

Decides whether to use retrieval or answer directly.
"""

from __future__ import annotations

from src.agents.router_agent import route_question
from src.graph.state import AgentState


def router_node(state: AgentState) -> dict:
    question = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            question = msg.content
            break

    decision = route_question(question)
    return {
        "route": decision["route"],
        "route_reason": decision["reason"],
    }