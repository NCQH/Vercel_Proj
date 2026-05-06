"""
Tutor agent that composes grounded responses from retrieved chunks.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List

from langchain_openai import ChatOpenAI

from src.config import DEFAULT_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model=DEFAULT_MODEL, api_key=OPENAI_API_KEY, temperature=0.3)

_ACADEMIC_CLASSIFIER_PROMPT = """You are a strict classifier.
Decide whether user question is related to studying, academic learning, school subjects,
course content, exam prep, concepts/definitions, or educational topics.

Return STRICT JSON only:
{"academic": true|false, "reason": "short"}
"""

_FALLBACK_ACADEMIC_KEYWORDS = (
    "học",
    "học tập",
    "bài giảng",
    "môn",
    "khái niệm",
    "định nghĩa",
    "lecture",
    "course",
    "chapter",
    "syllabus",
    "exam",
    "assignment",
    "machine learning",
    "thuật toán",
    "mô hình",
)

_LOW_CONFIDENCE_REPLY = (
    "Mình chưa thấy đủ thông tin đáng tin trong tài liệu để trả lời chắc chắn câu này. "
    "Bạn có thể cung cấp rõ hơn tên bài giảng/chương hoặc thêm tài liệu liên quan để mình tra cứu lại chính xác hơn."
)


def _format_context(chunks: List[dict]) -> str:
    if not chunks:
        return ""
    lines = []
    for i, c in enumerate(chunks, start=1):
        src = (c.get("metadata") or {}).get("source", "unknown")
        lines.append(f"[{i}] source={src}\n{c.get('text', '')}")
    return "\n\n".join(lines)


def _is_academic_question(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False

    try:
        resp = _llm.invoke(
            [
                {"role": "system", "content": _ACADEMIC_CLASSIFIER_PROMPT},
                {"role": "user", "content": q},
            ]
        )
        raw = (resp.content or "").strip()
        data = json.loads(raw)
        academic = bool(data.get("academic", False))
        reason = str(data.get("reason", ""))
        logger.info("[TUTOR] academic_classifier academic=%s reason=%s", academic, reason)
        return academic
    except Exception as exc:
        q_lower = q.lower()
        fallback = any(k in q_lower for k in _FALLBACK_ACADEMIC_KEYWORDS)
        logger.warning("[TUTOR] academic_classifier fallback=%s err=%s", fallback, exc)
        return fallback


def _max_retrieval_score(chunks: List[dict]) -> float:
    if not chunks:
        return 0.0
    return max(float(c.get("rerank_score", c.get("score", 0.0)) or 0.0) for c in chunks)


def generate_answer(question: str, chunks: List[dict]) -> Dict[str, str | List[str]]:
    """Generate a flexible, grounded tutoring answer."""
    context = _format_context(chunks)
    is_academic = _is_academic_question(question)
    max_score = _max_retrieval_score(chunks)
    sources_with_scores = []
    for chunk in chunks or []:
        meta = chunk.get("metadata") or {}
        source = str(meta.get("source") or "unknown")
        score = float(chunk.get("rerank_score", chunk.get("score", 0.0)) or 0.0)
        sources_with_scores.append((source, score))

    unique_sources = sorted({src for src, _ in sources_with_scores})
    top_sources = sorted(sources_with_scores, key=lambda x: x[1], reverse=True)[:5]
    logger.info(
        "[TUTOR] academic=%s chunks=%d max_score=%.4f sources=%s top_sources=%s",
        is_academic,
        len(chunks or []),
        max_score,
        unique_sources,
        top_sources,
    )

    # Policy: study-related question should retrieve first.
    # If retrieval confidence is low, answer with explicit uncertainty.
    if is_academic and max_score < 0.01:
        logger.info("[TUTOR] low confidence fallback triggered threshold=0.01")
        return {"answer": _LOW_CONFIDENCE_REPLY, "used_sources": []}

    if not context:
        logger.info("[TUTOR] no context, use direct tutor prompt")
        prompt = f"""Bạn là AI Teaching Assistant thân thiện.
Hãy trả lời tự nhiên, dễ hiểu, đúng trọng tâm cho câu hỏi sau.
Nếu cần, có thể nêu giả định rõ ràng và gợi ý người học hỏi rõ hơn.

Question: {question}
"""
        resp = _llm.invoke(prompt)
        return {"answer": (resp.content or "").strip(), "used_sources": []}

    logger.info("[TUTOR] grounded answer with retrieved context")
    prompt = f"""Bạn là AI Teaching Assistant.
Mục tiêu: hỗ trợ người học theo cách tự nhiên, rõ ràng, không máy móc.

Nguyên tắc trả lời:
- Ưu tiên bám vào context khi có thông tin liên quan.
- Có thể diễn giải linh hoạt để người học dễ hiểu.
- Nếu context chưa đủ cho một phần câu hỏi, nói rõ phần nào chưa chắc chắn.
- Không được bịa nguồn hay khẳng định chắc khi không có bằng chứng.
- Có thể đưa ví dụ ngắn nếu giúp làm rõ ý.
- Khi dùng thông tin từ context, chèn chỉ số chunk liên quan dạng [n] ngay sau ý đó (ví dụ: ... [2]).

Context:
{context}

Question: {question}
"""
    resp = _llm.invoke(prompt)
    answer = (resp.content or "").strip()

    # Map cited chunk indices [n] in answer -> source filenames
    cited_indices = {int(m.group(1)) for m in re.finditer(r"\[(\d+)\]", answer)}
    used_sources: List[str] = []
    for idx in sorted(cited_indices):
        if 1 <= idx <= len(chunks):
            src = str((chunks[idx - 1].get("metadata") or {}).get("source") or "")
            if src and src not in used_sources:
                used_sources.append(src)

    # Fallback: if model omitted markers but used context answer, keep top-1 source only.
    if not used_sources and chunks:
        src = str((chunks[0].get("metadata") or {}).get("source") or "")
        if src:
            used_sources = [src]

    return {"answer": answer, "used_sources": used_sources}
