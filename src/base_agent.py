"""
Basic agent loop using the OpenAI API.
Receives user input, calls tools as needed, and returns results.
"""

import logging
import json
from openai import OpenAI

from src.config import (
    DEFAULT_MODEL,
    LOG_LEVEL,
    MEMORY_CONTEXT_TURNS,
    MEMORY_FACT_MAX_DISTANCE,
    MEMORY_FACT_TOP_K,
    MEMORY_SUMMARY_MODEL,
    MEMORY_SUMMARY_TURNS,
    OPENAI_API_KEY,
)
from src.tools.tools import get_tool_schemas, execute_tool

# MEMORY (NEW)
from src.memory.memory_service import (
    debug_memory_recall,
    load_context_messages,
    load_memory,
    load_session_context_summary,
    refresh_session_summary,
    refresh_session_summary_with_llm,
    save_conversation_turn,
    save_memory,
)

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _extract_sources_from_tool_result(result):
    sources = []

    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                source = item.get("source")
                if source:
                    sources.append(str(source))
            elif isinstance(item, str) and item.strip():
                sources.append(item.strip())

    elif isinstance(result, dict):
        source = result.get("source")
        if source:
            sources.append(str(source))

    unique_sources = []
    seen = set()
    for source in sources:
        cleaned = source.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_sources.append(cleaned)

    return unique_sources


def _append_sources_if_missing(answer: str, sources):
    if not sources:
        return answer

    if "sources:" in answer.lower():
        return answer

    source_block = "\nSources:\n" + "\n".join(f"- {source}" for source in sources)
    return answer.rstrip() + source_block


SYSTEM_PROMPT = """
You are an AI Teaching Assistant.

You MUST use the tool `search_course_material` before answering any question related to:
- lectures
- course content
- documents
- definitions in the syllabus

Tool usage rules:
- Always call tool first if question is academic/content-based
- If tool returns multiple chunks, synthesize them
- If tool returns empty, say you don't know

You are not allowed to answer from memory for course-related questions.

Output format:
Answer: ...
Sources:
- source1
- source2
"""


def create_agent():
    """Create OpenAI client"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=OPENAI_API_KEY)


def run_agent_loop(
    client: OpenAI,
    user_input: str,
    user_id: str = "default",
    session_id: str = "default",
    max_turns: int = 10
) -> str:

    """
    Agent loop with tool calling + memory
    """

    # -----------------------
    # 0. LOAD MEMORY (NEW)
    # -----------------------
    memory = load_memory(
        user_id,
        user_input,
        top_k=MEMORY_FACT_TOP_K,
        max_distance=MEMORY_FACT_MAX_DISTANCE,
    ) or []
    context_messages = load_context_messages(
        user_id,
        max_turns=MEMORY_CONTEXT_TURNS,
    ) or []
    session_summary = load_session_context_summary(user_id)

    memory_block = ""
    if memory:
        memory_block = "\nUser Memory:\n" + "\n".join(f"- {m}" for m in memory)

    summary_block = ""
    if session_summary:
        summary_block = f"\nSession Summary:\n{session_summary}"

    # -----------------------
    # SYSTEM PROMPT (ENHANCED)
    # -----------------------
    system_prompt = SYSTEM_PROMPT + f"\n{memory_block}{summary_block}"

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(context_messages)
    messages.append({"role": "user", "content": user_input})

    tools = get_tool_schemas()

    # -----------------------
    # AGENT LOOP
    # -----------------------
    collected_sources = []
    for turn in range(max_turns):

        logger.info(f"Turn {turn + 1}/{max_turns}")
        logger.info(f"[MEMORY INPUT] {memory}")
        logger.info(f"[CONTEXT INPUT] loaded {len(context_messages)} messages")
        logger.info(f"[SUMMARY INPUT] loaded {1 if session_summary else 0} summary block")
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # -----------------------
        # STOP CONDITION
        # -----------------------
        if not message.tool_calls:

            final_answer = message.content or ""

            # -----------------------
            # SAVE MEMORY (FIXED)
            # -----------------------
            saved_count = save_memory(user_id, user_input)
            logger.info(f"[MEMORY SAVE] saved {saved_count} items")
            save_conversation_turn(
                user_id,
                user_input,
                str(final_answer),
                session_id=session_id,
            )
            logger.info("[CONTEXT SAVE] saved 1 turn")
            summary = refresh_session_summary_with_llm(
                client,
                user_id,
                model=MEMORY_SUMMARY_MODEL,
                max_turns_for_summary=MEMORY_SUMMARY_TURNS,
            )
            logger.info(f"[SUMMARY SAVE] length {len(summary)}")

            return _append_sources_if_missing(final_answer, collected_sources)

        # -----------------------
        # ADD ASSISTANT MESSAGE
        # -----------------------
        messages.append(message)

        # -----------------------
        # TOOL EXECUTION
        # -----------------------
        for tool_call in message.tool_calls:

            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            logger.info(f"Tool: {name}({args})")

            result = execute_tool(name, args)

            logger.info(f"Result: {str(result)[:200]}")

            if name == "search_course_material":
                collected_sources.extend(_extract_sources_from_tool_result(result))

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    return _append_sources_if_missing("Agent reached maximum number of turns.", collected_sources)


def main():
    """Interactive CLI"""

    client = create_agent()
    user_id = input("User ID (default: default): ").strip() or "default"
    session_id = input("Session ID (default: auto): ").strip() or "cli"

    print("Agentic App (type 'quit' to exit)")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        if user_input.startswith("/memory-debug"):
            debug_query = user_input.replace("/memory-debug", "", 1).strip()
            if not debug_query:
                print("\nUsage: /memory-debug <query>")
                continue

            rows = debug_memory_recall(
                user_id,
                debug_query,
                top_k=MEMORY_FACT_TOP_K,
                max_distance=MEMORY_FACT_MAX_DISTANCE,
            )
            print("\n[Memory Debug]")
            if not rows:
                print("No relevant memory found.")
                continue

            for idx, row in enumerate(rows, start=1):
                dist = row.get("distance")
                meta = row.get("metadata", {})
                print(f"{idx}. distance={dist} | type={meta.get('memory_type')} | source={meta.get('source')}")
                print(f"   text: {row.get('text')}")
            continue

        try:
            response = run_agent_loop(
                client,
                user_input,
                user_id=user_id,
                session_id=session_id,
            )
            print(f"\nAgent: {response}")

        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()