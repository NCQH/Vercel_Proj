"""
Router agent for deciding whether a query should use retrieval.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict

from langchain_openai import ChatOpenAI

from src.config import DEFAULT_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

_router_llm = ChatOpenAI(
    model=DEFAULT_MODEL,
    api_key=OPENAI_API_KEY,
    temperature=0,
)

_MATERIAL_TERMS = (
    "lecture",
    "course",
    "syllabus",
    "document",
    "chapter",
    "lesson",
    "definition",
    "slide",
    "reference",
    "citation",
    "bài giảng",
    "giáo trình",
    "chương",
    "tài liệu",
    "trích dẫn",
    "môn học",
    "học phần",
    "kiến thức",
)

_LOOKUP_VERBS = (
    "find",
    "lookup",
    "search",
    "quote",
    "cite",
    "extract",
    "show source",
    "tra cứu",
    "tìm",
    "trích",
)

_SMALL_TALK_TERMS = (
    "hello",
    "hi",
    "thanks",
    "thank you",
    "how are you",
    "xin chào",
    "cảm ơn",
)

_EXAM_PATTERN = re.compile(r"\b(quiz|exam|midterm|final|assignment|homework)\b", re.IGNORECASE)

_ROUTER_PROMPT = """You are routing classifier for AI Teaching Assistant.

Rule priority:
1) If question is related to studying/course content/learning tasks => route="retrieval".
2) If question is not related to studying (small talk, general life topics) => route="direct".

Be strict with rule (1): academic-related questions should retrieve first.

Return STRICT JSON only:
{"route":"retrieval|direct","reason":"short reason"}
"""


def _retrieval_signal_score(question: str) -> int:
    q = (question or "").lower().strip()
    score = 0

    if any(term in q for term in _MATERIAL_TERMS):
        score += 2
    if any(verb in q for verb in _LOOKUP_VERBS):
        score += 2
    if _EXAM_PATTERN.search(q):
        score += 2
    if "?" in q and len(q.split()) >= 8:
        score += 1

    return score


def _is_academic_question(question: str) -> bool:
    return _retrieval_signal_score(question) >= 2


def _heuristic_route(question: str) -> Dict[str, str]:
    q = (question or "").lower().strip()
    if not q:
        return {"route": "direct", "reason": "Heuristic: empty question"}

    if any(term in q for term in _SMALL_TALK_TERMS) and _retrieval_signal_score(q) < 2:
        return {"route": "direct", "reason": "Heuristic: small talk"}

    if _is_academic_question(q):
        return {"route": "retrieval", "reason": "Heuristic: academic question requires retrieval first"}

    return {"route": "direct", "reason": "Heuristic: non-academic/general question"}


def route_question(question: str) -> Dict[str, str]:
    """Return routing decision for orchestration graph using LLM + guardrail."""
    user_q = (question or "").strip()
    if not user_q:
        logger.info("[ROUTER] empty question -> direct")
        return {"route": "direct", "reason": "Empty question"}

    score = _retrieval_signal_score(user_q)
    is_academic = _is_academic_question(user_q)
    fallback = _heuristic_route(user_q)
    logger.info(
        "[ROUTER] precheck score=%s academic=%s fallback_route=%s",
        score,
        is_academic,
        fallback.get("route"),
    )

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
        reason = str(data.get("reason", "LLM decision"))

        if route not in ("retrieval", "direct"):
            logger.info("[ROUTER] invalid llm route=%s -> fallback=%s", route, fallback.get("route"))
            return fallback

        # Guardrail: academic question must go through retrieval.
        if is_academic:
            logger.info("[ROUTER] guardrail force retrieval score=%s reason=%s", score, reason)
            return {
                "route": "retrieval",
                "reason": "Guardrail: academic question requires retrieval first",
            }

        logger.info("[ROUTER] llm route=%s score=%s reason=%s", route, score, reason)
        return {"route": route, "reason": reason}

    except Exception as exc:
        logger.warning("[ROUTER] exception -> fallback route=%s err=%s", fallback.get("route"), exc)
        return fallback
