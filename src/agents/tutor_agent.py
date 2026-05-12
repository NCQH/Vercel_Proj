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


def _max_retrieval_score(chunks: List[dict]) -> float:
    if not chunks:
        return 0.0
    return max(
        float(c.get("rerank_score", c.get("relevance_score", c.get("score", 0.0))) or 0.0)
        for c in chunks
    )


def generate_answer(question: str, chunks: List[dict], is_academic: bool = False) -> Dict[str, str | List[str]]:
    """Generate a flexible, grounded tutoring answer."""
    context = _format_context(chunks)
    max_score = _max_retrieval_score(chunks)
    sources_with_scores = []
    for chunk in chunks or []:
        meta = chunk.get("metadata") or {}
        source = str(meta.get("source") or "unknown")
        score = float(chunk.get("rerank_score", chunk.get("relevance_score", chunk.get("score", 0.0))) or 0.0)
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
    # If retrieval confidence is low and evidence is too thin, answer with explicit uncertainty.
    if is_academic and max_score < 0.03 and len(chunks or []) < 2:
        logger.info("[TUTOR] low confidence fallback triggered threshold=0.03 min_chunks=2")
        return {"answer": _LOW_CONFIDENCE_REPLY, "used_sources": []}

    # Case 1: Non-academic (greetings, small talk, general help)
    if not is_academic:
        logger.info("[TUTOR] non-academic query, use natural response")
        prompt = f"""Bạn là AI Teaching Assistant thân thiện.
Hãy trả lời người dùng một cách tự nhiên, lịch sự và ngắn gọn.
Trả lời trực tiếp vào câu hỏi, không cần chia thành các phần như TL;DR hay Giải thích chính.

Question: {question}
"""
        resp = _llm.invoke(prompt)
        return {"answer": (resp.content or "").strip(), "used_sources": []}

    # Case 2: Academic but no context found
    if not context:
        logger.info("[TUTOR] academic query but no context, use direct structured prompt")
        prompt = f"""Bạn là AI Teaching Assistant thân thiện.
Hãy trả lời bằng tiếng Việt tự nhiên, rõ ràng, ngắn gọn đúng trọng tâm.

Định dạng bắt buộc:
1) TL;DR (1-2 câu)
2) Giải thích chính (2-5 gạch đầu dòng)
3) Ví dụ ngắn (nếu hữu ích, tối đa 3 dòng)

Quy tắc:
- Không lặp boilerplate kiểu "nếu bạn muốn tìm hiểu thêm..." ở mọi câu trả lời.
- Chỉ đặt câu hỏi gợi mở ở cuối khi thật sự còn mơ hồ hoặc thiếu dữ liệu.
- Không bịa thông tin; nếu chưa chắc, nói rõ mức độ chắc chắn.

Question: {question}
"""
        resp = _llm.invoke(prompt)
        return {"answer": (resp.content or "").strip(), "used_sources": []}

    # Case 3: Academic with retrieved context
    logger.info("[TUTOR] grounded academic answer with retrieved context")
    prompt = f"""Bạn là AI Teaching Assistant.
Mục tiêu: hỗ trợ người học theo cách tự nhiên, rõ ràng, không máy móc.

Định dạng bắt buộc:
1) TL;DR (1-2 câu)
2) Giải thích chính (3-6 gạch đầu dòng)
3) Ví dụ ngắn hoặc ứng dụng (nếu phù hợp, tối đa 4 dòng)

Nguyên tắc trả lời:
- Ưu tiên bám vào context khi có thông tin liên quan.
- Có thể diễn giải linh hoạt để người học dễ hiểu.
- Nếu context chưa đủ cho một phần câu hỏi, nói rõ phần nào chưa chắc chắn.
- Không được bịa nguồn hay khẳng định chắc khi không có bằng chứng.
- Khi dùng thông tin từ context, chèn chỉ số chunk liên quan dạng [n] ngay sau ý đó (ví dụ: ... [2]).
- Không lặp boilerplate kiểu "nếu bạn muốn tìm hiểu thêm..." trừ khi thật sự cần câu hỏi làm rõ.

Context:
{context}

Question: {question}
"""
    resp = _llm.invoke(prompt)
    answer = (resp.content or "").strip()

    # Map cited chunk indices [n] in answer -> source filenames
    cited_indices = {int(m.group(1)) for m in re.finditer(r"\[(\d+)\]", answer)}
    seen_files: dict[str, int] = {}
    for idx in sorted(cited_indices):
        if 1 <= idx <= len(chunks):
            src = str((chunks[idx - 1].get("metadata") or {}).get("source") or "")
            if src:
                base = src.rsplit("/", 1)[-1]
                if base not in seen_files:
                    seen_files[base] = idx

    used_sources = [f"[{idx}] {filename}" for filename, idx in sorted(seen_files.items(), key=lambda x: x[1])]

    # Fallback: if model omitted markers but context answer exists, keep answer with warning.
    if not used_sources and chunks:
        fallback_sources = []
        seen_fallback: set[str] = set()
        for i, c in enumerate(chunks[:2], start=1):
            src = str((c.get("metadata") or {}).get("source") or "")
            if not src:
                continue
            base = src.rsplit("/", 1)[-1]
            if base not in seen_fallback:
                fallback_sources.append(f"[{i}] {base}")
                seen_fallback.add(base)
        used_sources = fallback_sources
        warning_note = "⚠️ Lưu ý: Trả lời dưới đây dựa trên ngữ cảnh truy xuất, nhưng mô hình chưa chèn chỉ mục trích dẫn [n] rõ ràng."
        if warning_note not in answer:
            answer = f"{warning_note}\n\n{answer}"
        logger.warning("[TUTOR] missing citation markers -> auto-attach top sources=%s", used_sources)

    return {"answer": answer, "used_sources": used_sources}
