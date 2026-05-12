import json
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from api.models.schemas import ChatRequest
from api.lib.supabase import (
    _get_user_profile,
    _get_recent_chat_history,
    _get_allowed_sources_and_collections,
    _get_allowed_sources,
    _save_chat_message,
    _safe_user_id
)
from src.base_agent import run_agent
from src.graph.builder import graph
# Note: Re-importing sanitization helpers if they were moved, or keeping them local for now
# For simplicity, I will include the sanitization helpers here if they are only for chat.
import re

router = APIRouter(prefix="/api/chat")
logger = logging.getLogger(__name__)

_MAX_CHAT_MESSAGE_LEN = 4000
_MAX_PREFERRED_SOURCES = 20
_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "reveal hidden",
    "jailbreak",
    "bypass policy",
)

def _sanitize_chat_message(raw: str) -> str:
    text = (raw or "").replace("\x00", " ")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for pat in _INJECTION_PATTERNS:
        text = re.sub(re.escape(pat), "[redacted]", text, flags=re.IGNORECASE)
    return text[:_MAX_CHAT_MESSAGE_LEN]

def _sanitize_preferred_sources(raw_sources: list[str] | None, allowed_sources: list[str]) -> list[str]:
    allowed = set(allowed_sources or [])
    clean = []
    for src in raw_sources or []:
        if not isinstance(src, str):
            continue
        s = src.strip()[:180]
        if not s:
            continue
        if allowed and s not in allowed:
            continue
        if s not in clean:
            clean.append(s)
        if len(clean) >= _MAX_PREFERRED_SOURCES:
            break
    return clean

@router.post("")
def chat(request: ChatRequest):
    try:
        safe_user = _safe_user_id(request.user_id)
        profile = _get_user_profile(safe_user)
        history = _get_recent_chat_history(safe_user, request.session_id)
        allowed_sources, allowed_collections = _get_allowed_sources_and_collections(safe_user)
        preferred_sources = _sanitize_preferred_sources(request.preferred_sources, allowed_sources)
        safe_message = _sanitize_chat_message(request.message)
        if not safe_message:
            raise HTTPException(status_code=400, detail="Empty or invalid message")
        
        response, state = run_agent(
            safe_message,
            user_id=safe_user,
            session_id=request.session_id,
            allowed_sources=allowed_sources,
            allowed_collections=allowed_collections,
            preferred_sources=preferred_sources,
        )

        sources = state.get("sources", []) if isinstance(state, dict) else []
        if not isinstance(sources, list):
            sources = []

        _save_chat_message(safe_user, request.session_id, "user", safe_message)
        _save_chat_message(
            safe_user,
            request.session_id,
            "assistant",
            response,
            citations=[str(s) for s in sources if str(s).strip()],
        )

        return {"reply": response, "sources": sources}
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=f"Agent encountered an error: {str(e)}")

@router.get("/history")
def chat_history(user_id: str = "", session_id: str = "web_session", limit: int = 30):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = _get_recent_chat_history(safe_user, session_id, limit=max(1, min(limit, 100)))
    return {"ok": True, "user_id": safe_user, "session_id": session_id, "items": items}

@router.get("/sessions")
def chat_sessions(user_id: str = "", limit: int = 20):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    from api.lib.supabase import _list_chat_sessions
    items = _list_chat_sessions(safe_user, limit=max(1, min(limit, 100)))
    return {"ok": True, "user_id": safe_user, "items": items}

@router.get("/sources")
def chat_sources(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = _get_allowed_sources(safe_user)
    return {"ok": True, "user_id": safe_user, "items": items}

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        yield (" " * 2048) + "\n"
        
        try:
            safe_user = _safe_user_id(request.user_id)
            profile = _get_user_profile(safe_user)
            history = _get_recent_chat_history(safe_user, request.session_id)
            allowed_sources, allowed_collections = _get_allowed_sources_and_collections(safe_user)
            preferred_sources = _sanitize_preferred_sources(request.preferred_sources, allowed_sources)
            safe_message = _sanitize_chat_message(request.message)
            if not safe_message:
                yield "\n[ERROR] Empty or invalid message"
                return

            initial_state = {
                "messages": [HumanMessage(content=safe_message)],
                "user_id": safe_user,
                "session_id": request.session_id,
                "sources": [],
                "allowed_sources": allowed_sources,
                "allowed_collections": allowed_collections,
                "preferred_sources": preferred_sources,
                "memory_block": "",
                "summary_block": "",
                "route": "",
                "route_reason": "",
                "retrieved_chunks": [],
                "final_answer": "",
                "guardrail_passed": True,
                "guardrail_rejection": "",
                "is_academic": False,
            }

            final_answer = ""
            sources = []

            async for event in graph.astream_events(initial_state, version="v2", config={"recursion_limit": 25}):
                kind = event["event"]
                name = event["name"]

                if kind == "on_chain_start":
                    if name == "load_memory":
                        yield '__STEP__:Loading memory context...\n'
                    elif name == "guardrail_input":
                        yield '__STEP__:Checking content safety & intent...\n'
                    elif name == "retrieval":
                        yield '__STEP__:Searching knowledge base...\n'
                    elif name == "tutor":
                        yield '__STEP__:Drafting response...\n'
                    elif name == "save_memory":
                        yield '__STEP__:Updating context...\n'
                
                elif kind == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict):
                        if "final_answer" in output and output["final_answer"]:
                            final_answer = output["final_answer"]
                            sources = output.get("sources", [])
                        
                        if "messages" in output:
                            messages = output.get("messages", [])
                            for msg in reversed(messages):
                                if getattr(msg, "type", "") == "ai" and not getattr(msg, "tool_calls", None):
                                    final_answer = msg.content or ""
                                    sources = output.get("sources", [])
                                    break

            text = final_answer or ""

            _save_chat_message(safe_user, request.session_id, "user", safe_message)
            _save_chat_message(
                safe_user,
                request.session_id,
                "assistant",
                text,
                citations=[str(s) for s in sources if str(s).strip()],
            )

            yield '__STEP__:Done\n'

            words = text.split(" ")
            for i, word in enumerate(words):
                chunk = (word + " ") if i < len(words) - 1 else word
                yield f"__CHUNK__:{chunk}\n"
                await asyncio.sleep(0.015)

            if sources:
                yield f"__SOURCES__:{json.dumps(sources, ensure_ascii=False)}\n"
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"\n[ERROR] Agent encountered an error: {str(e)}"

    return StreamingResponse(event_generator(), media_type="text/plain; charset=utf-8")
