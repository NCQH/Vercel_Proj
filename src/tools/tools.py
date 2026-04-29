"""
LangChain Tool definitions for the AI Teaching Assistant.

Each tool is decorated with @tool so LangGraph's ToolNode can
execute them automatically.  The existing RAG retriever is reused
as-is via `search_course_material`.
"""

import ast
import ipaddress
import json
import socket
from typing import Union
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool

from src.rag.retriever import retrieve_dense, retrieve_hybrid, retrieve_sparse


# ------------------------------------------------------------------
# Internal safety helpers
# ------------------------------------------------------------------

_ALLOWED_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


def _safe_eval_expr(expression: str) -> Union[int, float]:
    node = ast.parse(expression, mode="eval")

    def _eval(n: ast.AST) -> Union[int, float]:
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp):
            op_type = type(n.op)
            if op_type not in _ALLOWED_BIN_OPS:
                raise ValueError("Unsupported operator")
            return _ALLOWED_BIN_OPS[op_type](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp):
            op_type = type(n.op)
            if op_type not in _ALLOWED_UNARY_OPS:
                raise ValueError("Unsupported unary operator")
            return _ALLOWED_UNARY_OPS[op_type](_eval(n.operand))
        raise ValueError("Unsupported expression")

    return _eval(node)


def _is_private_host(hostname: str) -> bool:
    if not hostname:
        return True
    if hostname.lower() in {"localhost"}:
        return True

    try:
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            ip_str = info[4][0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return True
    except Exception:
        return True

    return False


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------

@tool
def search_web(query: str) -> str:
    """Search for information on the web (placeholder)."""
    return f"Search results for: {query}"


@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression safely."""
    try:
        result = _safe_eval_expr(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool
def fetch_url(url: str) -> str:
    """Fetch content from a URL and return the first 2000 characters."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return "Error: Only http/https URLs are allowed"
        if _is_private_host(parsed.hostname or ""):
            return "Error: Host is not allowed"

        resp = httpx.get(url, timeout=10, follow_redirects=True)
        return resp.text[:2000]
    except Exception as e:
        return f"Error: {e}"


@tool
def search_course_material(query: str, mode: str = "hybrid") -> str:
    """Search for relevant information in the course materials.

    Args:
        query: The search query about course content.
        mode: Retrieval mode — one of 'dense', 'sparse', or 'hybrid' (default).
    """
    if mode == "dense":
        chunks = retrieve_dense(query)
    elif mode == "sparse":
        chunks = retrieve_sparse(query)
    elif mode == "hybrid":
        chunks = retrieve_hybrid(query)
    else:
        chunks = retrieve_dense(query)

    results = [
        {
            "text": c["text"],
            "source": c["metadata"].get("source"),
            "score": c["score"],
        }
        for c in chunks
    ]

    return json.dumps(results, ensure_ascii=False)


# ------------------------------------------------------------------
# Convenience list used by the graph builder
# ------------------------------------------------------------------

ALL_TOOLS = [
    search_web,
    calculate,
    fetch_url,
    search_course_material,
]
