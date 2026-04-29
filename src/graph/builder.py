"""
LangGraph – Multi-agent Graph Builder for AI Teaching Assistant.

Flow:

    load_memory -> router -> (retrieval -> tutor | tutor) -> save_memory -> END
"""

from langgraph.graph import END, StateGraph

from src.graph.state import AgentState
from src.graph.nodes.load_memory_node import load_memory_node
from src.graph.nodes.router_node import router_node
from src.graph.nodes.retrieval_node import retrieval_node
from src.graph.nodes.tutor_node import tutor_node
from src.graph.nodes.save_memory_node import save_memory_node


def route_after_router(state: AgentState) -> str:
    """Route to retrieval branch or direct tutor branch."""
    return "retrieval" if state.get("route") == "retrieval" else "direct"


builder = StateGraph(AgentState)

# Nodes
builder.add_node("load_memory", load_memory_node)
builder.add_node("router", router_node)
builder.add_node("retrieval", retrieval_node)
builder.add_node("tutor", tutor_node)
builder.add_node("save_memory", save_memory_node)

# Edges
builder.set_entry_point("load_memory")
builder.add_edge("load_memory", "router")

builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "retrieval": "retrieval",
        "direct": "tutor",
    },
)

builder.add_edge("retrieval", "tutor")
builder.add_edge("tutor", "save_memory")
builder.add_edge("save_memory", END)

# Compile
graph = builder.compile()