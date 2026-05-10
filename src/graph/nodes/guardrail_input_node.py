"""
LangGraph node: input guardrail check.

Validates user input for content safety before processing.
"""

from __future__ import annotations

import logging

from src.agents.guardrail_agent import check_input_safety, get_rejection_message
from src.graph.state import AgentState

logger = logging.getLogger(__name__)


def guardrail_input_node(state: AgentState) -> dict:
    """Check if user input is safe to process."""
    messages = state.get("messages", [])
    user_id = state.get("user_id", "unknown")
    session_id = state.get("session_id", "unknown")

    if not messages:
        logger.warning("[GUARDRAIL_INPUT] no messages in state user_id=%s session_id=%s", user_id, session_id)
        return {"guardrail_passed": True}

    last_message = messages[-1]
    user_input = getattr(last_message, "content", "")
    input_preview = (user_input[:100] + "...") if len(user_input) > 100 else user_input

    result = check_input_safety(user_input)
    safe = result.get("safe", True)
    category = result.get("category", "unknown")
    reason = result.get("reason", "")

    if not safe:
        rejection_msg = get_rejection_message(category)
        logger.warning(
            "[GUARDRAIL_INPUT] VIOLATION DETECTED | user_id=%s session_id=%s category=%s reason=%s input_preview=%s",
            user_id,
            session_id,
            category,
            reason,
            repr(input_preview),
        )
        return {
            "guardrail_passed": False,
            "guardrail_rejection": rejection_msg,
            "final_answer": rejection_msg,
        }

    logger.info("[GUARDRAIL_INPUT] passed user_id=%s session_id=%s", user_id, session_id)
    return {"guardrail_passed": True}
