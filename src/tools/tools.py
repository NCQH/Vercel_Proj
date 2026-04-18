"""
Tool definitions for the agent.
Add new tools by creating a function and registering it in the TOOLS dict.
"""

import httpx


def search_web(query: str) -> str:
    """Search for information on the web (placeholder)."""
    return f"Search results for: {query}"


def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        return resp.text[:2000]
    except Exception as e:
        return f"Error: {e}"


def get_tool_schemas():
    schemas = []
    for name, tool in TOOLS.items():
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        k: {"type": "string"}
                        for k in tool["parameters"].keys()
                    },
                    "required": list(tool["parameters"].keys()),
                },
            }
        })
    return schemas


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name."""
    tool = TOOLS.get(name)
    if not tool:
        return f"Tool '{name}' does not exist"
    return tool["fn"](**args)

from src.rag.retriever import retrieve_dense, retrieve_hybrid, retrieve_sparse

def search_course_material(query: str, mode: str = "hybrid"):
    if mode == "dense":
        chunks = retrieve_dense(query)

    elif mode == "sparse":
        chunks = retrieve_sparse(query)

    elif mode == "hybrid":
        chunks = retrieve_hybrid(query)

    else:
        chunks = retrieve_dense(query)

    return [
        {
            "text": c["text"],
            "source": c["metadata"].get("source"),
            "score": c["score"]
        }
        for c in chunks
    ]

TOOLS = {
    "search_web": {
        "fn": search_web,
        "description": "Search for information on the web",
        "parameters": {"query": "string"},
    },
    "calculate": {
        "fn": calculate,
        "description": "Evaluate a math expression",
        "parameters": {"expression": "string"},
    },
    "fetch_url": {
        "fn": fetch_url,
        "description": "Fetch content from a URL",
        "parameters": {"url": "string"},
    },
    "search_course_material": {
        "fn": search_course_material,
        "description": "Search for relevant information in the course materials",
        "parameters": {"query": "string", "mode": "string (dense | sparse | hybrid, default: hybrid)"},
    },
}

