"""
Basic agent loop using the Anthropic Claude API.
Receives user input, calls tools as needed, and returns results.
"""

import logging
from openai import OpenAI
from src.config import DEFAULT_MODEL, LOG_LEVEL, OPENAI_API_KEY
from src.tools import get_tool_schemas, execute_tool
import json

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an AI Teaching Assistant that helps students understand course materials.

Capabilities:
- Answer questions about lecture slides and course documents
- Summarize course material
- Provide explanations with references to the material

Rules:
- Always search the course material before answering questions about the course.
- Use the search_course_material tool to retrieve relevant information.
- If the answer is not in the materials, say that you cannot find it in the course documents.

Think step by step and use tools when necessary.
"""


def create_agent():
    """Create an agent with the OpenAI client."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured. Check your .env file")
    return OpenAI(api_key=OPENAI_API_KEY)


def run_agent_loop(client: OpenAI, user_input: str, max_turns: int = 10) -> str:
    """
    Run the agent loop: send message -> receive response -> call tool -> repeat.

    Args:
        client: OpenAI client
        user_input: User's question or request
        max_turns: Maximum number of tool-calling turns

    Returns:
        The agent's final response
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    tools = get_tool_schemas()

    for turn in range(max_turns):
        logger.info(f"Turn {turn + 1}/{max_turns}")

        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = response.choices[0].message
        # If agent stops (no more tool calls)
        if not message.tool_calls:
            return message.content
        
        # Handle tool calls
        messages.append(message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            logger.info(f"Calling tool: {name}({args})")

            result = execute_tool(name, args)

            logger.info(f"Result: {result[:200]}")

            # append tool result
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    return "Agent reached the maximum number of processing turns."


def main():
    """Interactive loop - enter a prompt and receive results."""
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
