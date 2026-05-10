"""
Retrieval agent that returns structured retrieval outputs.
"""

from __future__ import annotations

from typing import Dict, List

from src.rag.retriever import retrieve_dense, retrieve_hybrid, retrieve_sparse


def run(question: str, mode: str = "hybrid", top_k: int = 5, collections: List[str] = None) -> Dict[str, List[dict]]:
    if not collections:
        collections = ["default"]

    all_chunks = []
    for col in collections:
        if mode == "dense":
            chunks = retrieve_dense(question, top_k=top_k, user_id=col)
        elif mode == "sparse":
            chunks = retrieve_sparse(question, top_k=top_k, user_id=col)
        else:
            chunks = retrieve_hybrid(question, top_k=top_k, user_id=col)
        all_chunks.extend(chunks)

    # Sort combined chunks using normalized relevance priority.
    all_chunks.sort(
        key=lambda x: x.get("rerank_score", x.get("relevance_score", x.get("score", 0.0))),
        reverse=True,
    )
    
    # Deduplicate by key if needed, or just take top_k
    seen = set()
    final_chunks = []
    for c in all_chunks:
        text = c.get("text", "")
        if text not in seen:
            seen.add(text)
            final_chunks.append(c)
        if len(final_chunks) == top_k:
            break

    chunks = final_chunks

    sources: List[str] = []
    for c in chunks:
        src = (c.get("metadata") or {}).get("source")
        if src and str(src) not in sources:
            sources.append(str(src))

    return {
        "chunks": chunks,
        "sources": sources,
    }