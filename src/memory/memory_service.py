from src.memory.memory_extract import extract_memory
from src.memory.memory_store import (
    add_memory,
    append_conversation_turn,
    load_recent_conversation,
    load_session_summary,
    query_memory,
    query_memory_records,
    save_session_summary,
)


DEFAULT_FACT_TOP_K = 5
DEFAULT_FACT_MAX_DISTANCE = 1.1


def load_memory(
    user_id: str,
    query: str,
    top_k: int = DEFAULT_FACT_TOP_K,
    max_distance: float = DEFAULT_FACT_MAX_DISTANCE,
):
    return query_memory(user_id, query, top_k=top_k, max_distance=max_distance)


def load_context_messages(user_id: str, max_turns: int = 3):
    return load_recent_conversation(user_id, max_turns=max_turns)


def load_session_context_summary(user_id: str):
    return load_session_summary(user_id)


def debug_memory_recall(
    user_id: str,
    query: str,
    top_k: int = DEFAULT_FACT_TOP_K,
    max_distance: float = DEFAULT_FACT_MAX_DISTANCE,
):
    return query_memory_records(
        user_id,
        query,
        top_k=top_k,
        max_distance=max_distance,
    )


def save_memory(user_id: str, text: str):
    text_l = text.lower()

    # Explicit intents that indicate users want long-term memory.
    explicit_triggers = [
        "tôi thích",
        "tôi không thích",
        "tôi là",
        "tên tôi",
        "hãy nhớ",
        "nhớ rằng",
        "remember",
        "remember that",
        "i like",
        "i don't like",
        "my preference",
        "my name is",
        "i am",
    ]

    extracted = extract_memory(text)

    candidates = list(extracted)
    if any(t in text_l for t in explicit_triggers):
        candidates.append(text)

    # Deduplicate while keeping original order.
    unique_candidates = []
    seen = set()
    for c in candidates:
        c_norm = c.strip()
        if not c_norm:
            continue
        if c_norm in seen:
            continue
        seen.add(c_norm)
        unique_candidates.append(c_norm)

    for memory in unique_candidates:
        add_memory(
            user_id,
            memory,
            memory_type="fact",
            source="user",
            confidence=0.9,
            tags=["preference", "profile"],
        )

    return len(unique_candidates)


def _summary_from_turns(turns):
    if not turns:
        return ""

    user_messages = [
        (m.get("content") or "").strip()
        for m in turns
        if m.get("role") == "user"
    ]
    assistant_messages = [
        (m.get("content") or "").strip()
        for m in turns
        if m.get("role") == "assistant"
    ]

    user_messages = [m for m in user_messages if m]
    assistant_messages = [m for m in assistant_messages if m]

    recent_user = user_messages[-3:]
    recent_assistant = assistant_messages[-2:]

    facts = []
    for msg in user_messages[-8:]:
        facts.extend(extract_memory(msg))

    # dedupe facts while preserving order
    seen = set()
    dedup_facts = []
    for fact in facts:
        key = fact.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        dedup_facts.append(key)

    lines = []
    if recent_user:
        lines.append("Recent user intents:")
        lines.extend(f"- {m}" for m in recent_user)

    if dedup_facts:
        lines.append("Stable user facts:")
        lines.extend(f"- {f}" for f in dedup_facts[-5:])

    if recent_assistant:
        lines.append("Recent assistant commitments:")
        lines.extend(f"- {m}" for m in recent_assistant)

    return "\n".join(lines)


def refresh_session_summary(user_id: str, max_turns_for_summary: int = 12):
    turns = load_recent_conversation(user_id, max_turns=max_turns_for_summary)
    summary = _summary_from_turns(turns)
    if summary:
        save_session_summary(user_id, summary)
    return summary


def refresh_session_summary_with_llm(
    client,
    user_id: str,
    model: str,
    max_turns_for_summary: int = 12,
):
    turns = load_recent_conversation(user_id, max_turns=max_turns_for_summary)
    if not turns:
        return load_session_summary(user_id)

    previous_summary = load_session_summary(user_id)
    transcript_lines = []
    for m in turns:
        role = m.get("role", "user")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        transcript_lines.append(f"{role}: {content}")

    transcript = "\n".join(transcript_lines[-24:])

    system_prompt = (
        "You summarize user-agent conversation memory for future context recall. "
        "Keep only durable user preferences, goals, constraints, and recent commitments. "
        "Output concise bullet points in plain text."
    )
    user_prompt = (
        f"Previous summary:\n{previous_summary or '(none)'}\n\n"
        f"Recent transcript:\n{transcript}\n\n"
        "Write an updated memory summary (max 8 bullets, max 700 characters)."
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        summary = (resp.choices[0].message.content or "").strip()
        if summary:
            save_session_summary(user_id, summary)
            return summary
    except Exception:
        pass

    return refresh_session_summary(user_id, max_turns_for_summary=max_turns_for_summary)


def save_conversation_turn(
    user_id: str,
    user_text: str,
    assistant_text: str,
    session_id: str = "default",
):
    append_conversation_turn(user_id, user_text, assistant_text, session_id=session_id)


