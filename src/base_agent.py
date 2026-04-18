"""
Basic agent loop using the OpenAI API.
Receives user input, calls tools as needed, and returns results.
"""

import logging
import json
from openai import OpenAI

from src.config import DEFAULT_MODEL, LOG_LEVEL, OPENAI_API_KEY
from src.tools.tools import get_tool_schemas, execute_tool

# MEMORY (NEW)
from src.memory.memory_service import load_memory, save_memory

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


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
    max_turns: int = 10
) -> str:

    """
    Agent loop with tool calling + memory
    """

    # -----------------------
    # 0. LOAD MEMORY (NEW)
    # -----------------------
    memory = load_memory(user_id, user_input) or []

    memory_block = ""
    if memory:
        memory_block = "\nUser Memory:\n" + "\n".join(f"- {m}" for m in memory)

    # -----------------------
    # SYSTEM PROMPT (ENHANCED)
    # -----------------------
    system_prompt = SYSTEM_PROMPT + f"\n{memory_block}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    tools = get_tool_schemas()

    # -----------------------
    # AGENT LOOP
    # -----------------------
    for turn in range(max_turns):

        logger.info(f"Turn {turn + 1}/{max_turns}")
        logger.info(f"[MEMORY INPUT] {memory}")
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

            final_answer = message.content

            # -----------------------
            # SAVE MEMORY (FIXED)
            # -----------------------
            save_memory(user_id, user_input)

            return final_answer

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

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    return "Agent reached maximum number of turns."


def main():
    """Interactive CLI"""

    client = create_agent()

    print("Agentic App (type 'quit' to exit)")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        try:
            response = run_agent_loop(client, user_input)
            print(f"\nAgent: {response}")

        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()