"""
LangGraph State Definition for AI Teaching Assistant.

The state flows through the graph, carrying messages, metadata, and
memory context needed by each node.
"""

from typing import Annotated, List, Optional, Sequence
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Central state passed between every node in the graph.

    Attributes:
        messages: Chat history (system + user + assistant + tool messages).
                  Uses the `add_messages` reducer so each node can *append*
                  rather than replace.
        user_id:  Identifies the user for memory look-ups.
        session_id: Groups turns within one conversation session.
        sources:  Citation sources collected during tool execution.
        memory_block: Formatted long-term memory string injected into system prompt.
        summary_block: Running session summary injected into system prompt.
        route: Routing decision from router agent ('retrieval' | 'direct').
        route_reason: Human-readable reason for route decision.
        retrieved_chunks: Structured chunks returned by retrieval agent.
        final_answer: Final answer text prepared by tutor/direct branch.
"""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    session_id: str
    sources: List[str]
    memory_block: str
    summary_block: str
    route: str
    route_reason: str
    retrieved_chunks: List[dict]
    final_answer: str