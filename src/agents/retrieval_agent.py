"""
Retrieval agent that returns structured retrieval outputs.
"""

from __future__ import annotations

from typing import Dict, List

from src.rag.retriever import retrieve_dense, retrieve_hybrid, retrieve_sparse


def run(question: str, mode: str = "hybrid", top_k: int = 5) -> Dict[str, List[dict]]:
    if mode == "dense":
        chunks = retrieve_dense(question, top_k=top_k)
    elif mode == "sparse":
        chunks = retrieve_sparse(question, top_k=top_k)
    else:
        chunks = retrieve_hybrid(question, top_k=top_k)

    sources: List[str] = []
    for c in chunks:
        src = (c.get("metadata") or {}).get("source")
        if src and str(src) not in sources:
            sources.append(str(src))

    return {
        "chunks": chunks,
        "sources": sources,
    }