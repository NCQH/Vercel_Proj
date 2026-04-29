"""
Router agent for deciding whether a query should use retrieval.
"""

from __future__ import annotations

import json
from typing import Dict

from langchain_openai import ChatOpenAI

from src.config import DEFAULT_MODEL, OPENAI_API_KEY

_router_llm = ChatOpenAI(
    model=DEFAULT_MODEL,
    api_key=OPENAI_API_KEY,
    temperature=0,
)

_ACADEMIC_HINTS = (
    "lecture",
    "course",
    "syllabus",
    "document",
    "chapter",
    "lesson",
    "definition",
    "slide",
    "bài giảng",
    "giáo trình",
    "chương",
)

_ROUTER_PROMPT = """You are a routing classifier for an AI Teaching Assistant.

Given a user question, decide one route:
- retrieval: if the question needs course materials, lecture facts, syllabus definitions,
  policy details, or any factual lookup from documents.
- direct: if it is greeting, small talk, generic conversation, or does not require document lookup.

Return STRICT JSON only with this schema:
{"route":"retrieval|direct","reason":"short reason"}
"""


def _heuristic_route(question: str) -> Dict[str, str]:
    q = (question or "").lower()
    needs_retrieval = any(h in q for h in _ACADEMIC_HINTS)
    return {
        "route": "retrieval" if needs_retrieval else "direct",
        "reason": "Heuristic fallback: academic hint matched" if needs_retrieval else "Heuristic fallback: general conversation",
    }


def route_question(question: str) -> Dict[str, str]:
    """Return routing decision for orchestration graph using LLM."""
    user_q = (question or "").strip()
    if not user_q:
        return {"route": "direct", "reason": "Empty question"}

    try:
        resp = _router_llm.invoke(
            [
                {"role": "system", "content": _ROUTER_PROMPT},
                {"role": "user", "content": user_q},
            ]
        )
        raw = (resp.content or "").strip()
        data = json.loads(raw)

        route = data.get("route", "")
        reason = data.get("reason", "LLM decision")

        if route not in ("retrieval", "direct"):
            return _heuristic_route(user_q)

        return {"route": route, "reason": str(reason)}

    except Exception:
        # Safe fallback to avoid crashing the graph.
        return _heuristic_route(user_q)
