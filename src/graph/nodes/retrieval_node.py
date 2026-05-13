"""
LangGraph node: retrieval

Calls retrieval agent and stores chunks + sources in state.
"""

from __future__ import annotations

import logging

from src.agents.retrieval_agent import run as run_retrieval
from src.graph.state import AgentState

logger = logging.getLogger(__name__)

_MIN_RELEVANCE_SCORE = 0.01


def _score_of(chunk: dict) -> float:
    return float(chunk.get("rerank_score", chunk.get("relevance_score", chunk.get("score", 0.0))) or 0.0)


def _src_of(chunk: dict) -> str:
    return str((chunk.get("metadata") or {}).get("source") or "")


def retrieval_node(state: AgentState) -> dict:
    question = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            question = msg.content
            break

    allowed_collections = state.get("allowed_collections") or [state.get("user_id", "default")]
    allowed_sources = state.get("allowed_sources") or []
    preferred_sources = state.get("preferred_sources") or []

    preferred_result = {"chunks": []}
    if preferred_sources:
        preferred_allowed = [src for src in preferred_sources if not allowed_sources or src in allowed_sources]
        if preferred_allowed:
            preferred_result = run_retrieval(
                question,
                mode="hybrid",
                top_k=5,
                collections=allowed_collections,
                allowed_sources=preferred_allowed,
            )

    result = run_retrieval(
        question,
        mode="hybrid",
        top_k=8 if preferred_sources else 5,
        collections=allowed_collections,
        allowed_sources=allowed_sources,
    )

    preferred_chunks = preferred_result.get("chunks", [])
    general_chunks = result.get("chunks", [])
    chunks = preferred_chunks + general_chunks
    logger.info(
        "[RETRIEVAL] DB-filtered chunks=%d allowed_collections=%s allowed_sources=%d preferred_sources=%d",
        len(chunks),
        allowed_collections,
        len(allowed_sources),
        len(preferred_sources),
    )

    if preferred_sources:
        logger.info(
            "[RETRIEVAL] preferred-first preferred_chunks=%d general_chunks=%d",
            len(preferred_chunks),
            len(general_chunks),
        )

    pre_score_chunks = list(chunks)

    filtered = []
    seen_keys = set()
    dropped_low_score = 0
    dropped_dedup = 0
    for c in chunks:
        relevance = _score_of(c)
        if relevance < _MIN_RELEVANCE_SCORE:
            dropped_low_score += 1
            continue
        meta = c.get("metadata") or {}
        source = str(meta.get("source") or "")
        chunk_id = str(meta.get("chunk_id") or "")
        text_head = str(c.get("text") or "")[:120]
        dedup_key = f"{source}|{chunk_id}|{text_head}"
        if dedup_key in seen_keys:
            dropped_dedup += 1
            continue
        seen_keys.add(dedup_key)
        filtered.append(c)

    chunks = filtered
    logger.info(
        "[RETRIEVAL] after score+dedup chunks=%d dropped_low_score=%d dropped_dedup=%d min_score=%.3f",
        len(chunks),
        dropped_low_score,
        dropped_dedup,
        _MIN_RELEVANCE_SCORE,
    )

    if not chunks and pre_score_chunks:
        restored = sorted(pre_score_chunks, key=_score_of, reverse=True)[:3]
        chunks = restored
        logger.info(
            "[RETRIEVAL] fallback restored chunks=%d from source-filtered set",
            len(chunks),
        )

    if chunks:
        top_final = sorted(chunks, key=_score_of, reverse=True)[:5]
        logger.info(
            "[RETRIEVAL] final top=%s",
            [f"{_src_of(c)}:{_score_of(c):.4f}" for c in top_final],
        )

    # Only keep citations from top-ranked chunks likely used by tutor prompt.
    # This avoids appending every possible source from retrieval tail.
    top_chunks_for_citation = chunks[:3]
    sources = []
    for c in top_chunks_for_citation:
        src = str((c.get("metadata") or {}).get("source") or "")
        if src and src not in sources:
            sources.append(src)

    logger.info("[RETRIEVAL] citation sources=%s", sources)

    return {
        "retrieved_chunks": chunks,
        "sources": sources,
    }