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

    result = run_retrieval(
        question,
        mode="hybrid",
        top_k=5,
        user_id=state.get("user_id", "default"),
    )

    allowed_sources = set(state.get("allowed_sources") or [])
    preferred_sources = set(state.get("preferred_sources") or [])

    chunks = result.get("chunks", [])
    if allowed_sources:
        chunks = [
            c for c in chunks
            if str((c.get("metadata") or {}).get("source") or "") in allowed_sources
        ]

    if preferred_sources:
        preferred_chunks = []
        fallback_chunks = []
        for c in chunks:
            src = str((c.get("metadata") or {}).get("source") or "")
            if src in preferred_sources:
                preferred_chunks.append(c)
            else:
                fallback_chunks.append(c)
        chunks = preferred_chunks + fallback_chunks

    # Only keep citations from top-ranked chunks likely used by tutor prompt.
    # This avoids appending every possible source from retrieval tail.
    top_chunks_for_citation = chunks[:3]
    sources = []
    for c in top_chunks_for_citation:
        src = str((c.get("metadata") or {}).get("source") or "")
        if src and src not in sources:
            sources.append(src)

    return {
        "retrieved_chunks": chunks,
        "sources": sources,
    }