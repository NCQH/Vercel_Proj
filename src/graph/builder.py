from langgraph.graph import StateGraph
from graph.state import GraphState

from graph.nodes.retrieval_node import retrieval_node
from graph.nodes.reasoning_node import reasoning_node
from graph.nodes.citation_node import citation_node

builder = StateGraph(GraphState)

builder.add_node("retrieve", retrieval_node)
builder.add_node("reason", reasoning_node)
builder.add_node("cite", citation_node)

builder.set_entry_point("retrieve")

builder.add_edge("retrieve", "reason")
builder.add_edge("reason", "cite")

graph = builder.compile()