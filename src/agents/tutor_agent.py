"""
Tutor agent that composes grounded responses from retrieved chunks.
"""

from __future__ import annotations

from typing import Dict, List

from langchain_openai import ChatOpenAI

from src.config import DEFAULT_MODEL, OPENAI_API_KEY

_llm = ChatOpenAI(model=DEFAULT_MODEL, api_key=OPENAI_API_KEY, temperature=0.3)


def _format_context(chunks: List[dict]) -> str:
    if not chunks:
        return ""
    lines = []
    for i, c in enumerate(chunks, start=1):
        src = (c.get("metadata") or {}).get("source", "unknown")
        lines.append(f"[{i}] source={src}\n{c.get('text', '')}")
    return "\n\n".join(lines)


def generate_answer(question: str, chunks: List[dict]) -> Dict[str, str]:
    """Generate a flexible, grounded tutoring answer."""
    context = _format_context(chunks)

    if not context:
        prompt = f"""Bạn là AI Teaching Assistant thân thiện.
Hãy trả lời tự nhiên, dễ hiểu, đúng trọng tâm cho câu hỏi sau.
Nếu cần, có thể nêu giả định rõ ràng và gợi ý người học hỏi rõ hơn.

Question: {question}
"""
        resp = _llm.invoke(prompt)
        return {"answer": (resp.content or "").strip()}

    prompt = f"""Bạn là AI Teaching Assistant.
Mục tiêu: hỗ trợ người học theo cách tự nhiên, rõ ràng, không máy móc.

Nguyên tắc trả lời:
- Ưu tiên bám vào context khi có thông tin liên quan.
- Có thể diễn giải linh hoạt để người học dễ hiểu.
- Nếu context chưa đủ cho một phần câu hỏi, nói rõ phần nào chưa chắc chắn.
- Không được bịa nguồn hay khẳng định chắc khi không có bằng chứng.
- Có thể đưa ví dụ ngắn nếu giúp làm rõ ý.

Context:
{context}

Question: {question}
"""
    resp = _llm.invoke(prompt)
    return {"answer": (resp.content or "").strip()}
