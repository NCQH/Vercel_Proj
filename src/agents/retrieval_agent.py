"""
Retrieval agent that returns structured retrieval outputs.
"""

from __future__ import annotations

from typing import Dict, List

from src.rag.retriever import retrieve_dense, retrieve_hybrid, retrieve_sparse


def run(question: str, mode: str = "hybrid", top_k: int = 5, user_id: str = "default") -> Dict[str, List[dict]]:
    if mode == "dense":
        chunks = retrieve_dense(question, top_k=top_k, user_id=user_id)
    elif mode == "sparse":
        chunks = retrieve_sparse(question, top_k=top_k, user_id=user_id)
    else:
        chunks = retrieve_hybrid(question, top_k=top_k, user_id=user_id)

    sources: List[str] = []
    for c in chunks:
        src = (c.get("metadata") or {}).get("source")
        if src and str(src) not in sources:
            sources.append(str(src))

    return {
        "chunks": chunks,
        "sources": sources,
    }