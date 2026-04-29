"""
LangGraph node: agent

Calls ChatOpenAI (with tools bound) and returns the assistant message.
The graph's conditional edge will decide whether to route to the
tool_node or to save_memory_node based on whether tool_calls exist.
"""

import logging

from langchain_openai import ChatOpenAI

from src.config import DEFAULT_MODEL, OPENAI_API_KEY
from src.graph.state import AgentState
from src.tools.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# Create the LLM once with tools bound
llm = ChatOpenAI(
    model=DEFAULT_MODEL,
    api_key=OPENAI_API_KEY,
    temperature=0,
).bind_tools(ALL_TOOLS)


def agent_node(state: AgentState) -> dict:
    """Invoke the LLM with the current messages (which may include tool results)."""
    logger.info("[AGENT] invoking LLM with %d messages", len(state["messages"]))
    response = llm.invoke(state["messages"])
    return {"messages": [response]}
