import asyncio
import json
import logging
import os
import re
import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models.schemas import ChatRequest
from api.lib.supabase import (
    _get_user_profile,
    _get_recent_chat_history,
    _get_allowed_sources_and_collections,
    _get_allowed_sources,
    _save_chat_message,
    _safe_user_id,
    _list_chat_sessions,
)
from src.base_agent import run_agent

router = APIRouter(prefix="/api/chat")
logger = logging.getLogger(__name__)

_MAX_CHAT_MESSAGE_LEN = 4000
_MAX_PREFERRED_SOURCES = 20
_RUN_AGENT_TIMEOUT_SECONDS = float(os.getenv("CHAT_RUN_AGENT_TIMEOUT_SECONDS", "35"))

_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "reveal hidden",
    "jailbreak",
    "bypass policy",
)
_GUARDRAIL_PREFIX_KEYS = {"safe", "reason", "category", "route", "is_academic"}


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _log_step(rid: str, step: str, start: float) -> None:
    logger.info("[CHAT][%s] step=%s elapsed_ms=%.2f", rid, step, _elapsed_ms(start))


def _strip_guardrail_metadata_prefix(raw: str) -> str:
    text = (raw or "").lstrip()
    if not text.startswith("{"):
        return raw or ""

    try:
        parsed, idx = json.JSONDecoder().raw_decode(text)
    except Exception:
        return raw or ""

    if not isinstance(parsed, dict):
        return raw or ""

    if not _GUARDRAIL_PREFIX_KEYS.issubset(parsed.keys()):
        return raw or ""

    if not isinstance(parsed.get("safe"), bool):
        return raw or ""

    route = str(parsed.get("route", "")).strip().lower()
    if route not in {"retrieval", "direct"}:
        return raw or ""

    remainder = text[idx:].lstrip(" \t\r\n:-")
    logger.warning("[CHAT] stripped leaked guardrail metadata prefix route=%s", route)
    return remainder


def _sanitize_chat_message(raw: str) -> str:
    text = _strip_guardrail_metadata_prefix(raw)
    text = text.replace("\x00", " ")
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
async def chat(request: ChatRequest):
    rid = uuid4().hex[:8]
    req_start = time.perf_counter()

    try:
        safe_user = _safe_user_id(request.user_id)

        sanitize_start = time.perf_counter()
        safe_message = _sanitize_chat_message(request.message)
        if not safe_message:
            raise HTTPException(status_code=400, detail="Empty or invalid message")
        _log_step(rid, "sanitize", sanitize_start)

        fetch_start = time.perf_counter()
        profile_task = asyncio.to_thread(_get_user_profile, safe_user)
        history_task = asyncio.to_thread(_get_recent_chat_history, safe_user, request.session_id)
        access_task = asyncio.to_thread(_get_allowed_sources_and_collections, safe_user)
        _profile, _history, (allowed_sources, allowed_collections) = await asyncio.gather(
            profile_task,
            history_task,
            access_task,
        )
        _log_step(rid, "db_fetch_parallel", fetch_start)

        preferred_sources = _sanitize_preferred_sources(request.preferred_sources, allowed_sources)

        agent_start = time.perf_counter()
        response, state = await asyncio.wait_for(
            asyncio.to_thread(
                run_agent,
                safe_message,
                safe_user,
                request.session_id,
                allowed_sources,
                allowed_collections,
                preferred_sources,
            ),
            timeout=_RUN_AGENT_TIMEOUT_SECONDS,
        )
        _log_step(rid, "run_agent", agent_start)

        sources = state.get("sources", []) if isinstance(state, dict) else []
        if not isinstance(sources, list):
            sources = []
        clean_sources = [str(s) for s in sources if str(s).strip()]

        save_start = time.perf_counter()
        await asyncio.to_thread(_save_chat_message, safe_user, request.session_id, "user", safe_message)
        await asyncio.to_thread(
            _save_chat_message,
            safe_user,
            request.session_id,
            "assistant",
            response,
            clean_sources,
        )
        _log_step(rid, "save_messages", save_start)

        logger.info(
            "[CHAT][%s] done total_ms=%.2f msg_len=%d sources=%d",
            rid,
            _elapsed_ms(req_start),
            len(safe_message),
            len(clean_sources),
        )
        return {"reply": response, "sources": clean_sources}
    except asyncio.TimeoutError:
        logger.warning("[CHAT][%s] run_agent timeout total_ms=%.2f", rid, _elapsed_ms(req_start))
        raise HTTPException(status_code=504, detail="Agent timeout, please try again.")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[CHAT][%s] Chat error total_ms=%.2f", rid, _elapsed_ms(req_start))
        raise HTTPException(status_code=500, detail=f"Agent encountered an error: {str(e)}")


@router.get("/history")
async def chat_history(user_id: str = "", session_id: str = "web_session", limit: int = 30):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = await asyncio.to_thread(
        _get_recent_chat_history,
        safe_user,
        session_id,
        max(1, min(limit, 100)),
    )
    return {"ok": True, "user_id": safe_user, "session_id": session_id, "items": items}


@router.get("/sessions")
async def chat_sessions(user_id: str = "", limit: int = 20):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = await asyncio.to_thread(_list_chat_sessions, safe_user, max(1, min(limit, 100)))
    return {"ok": True, "user_id": safe_user, "items": items}


@router.get("/sources")
async def chat_sources(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = await asyncio.to_thread(_get_allowed_sources, safe_user)
    return {"ok": True, "user_id": safe_user, "items": items}


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    rid = uuid4().hex[:8]

    async def event_generator():
        req_start = time.perf_counter()
        yield (" " * 2048) + "\n"

        try:
            safe_user = _safe_user_id(request.user_id)

            sanitize_start = time.perf_counter()
            safe_message = _sanitize_chat_message(request.message)
            if not safe_message:
                yield "\n[ERROR] Empty or invalid message"
                return
            _log_step(rid, "stream_sanitize", sanitize_start)

            yield "__STEP__:Loading memory context...\n"
            fetch_start = time.perf_counter()
            profile_task = asyncio.to_thread(_get_user_profile, safe_user)
            history_task = asyncio.to_thread(_get_recent_chat_history, safe_user, request.session_id)
            access_task = asyncio.to_thread(_get_allowed_sources_and_collections, safe_user)
            _profile, _history, (allowed_sources, allowed_collections) = await asyncio.gather(
                profile_task,
                history_task,
                access_task,
            )
            _log_step(rid, "stream_db_fetch_parallel", fetch_start)
            await asyncio.sleep(0)

            yield "__STEP__:Checking content safety & intent...\n"
            preferred_sources = _sanitize_preferred_sources(request.preferred_sources, allowed_sources)
            await asyncio.sleep(0)

            yield "__STEP__:Searching knowledge base...\n"
            await asyncio.sleep(0)

            yield "__STEP__:Drafting response...\n"
            agent_start = time.perf_counter()
            final_answer, state = await asyncio.wait_for(
                asyncio.to_thread(
                    run_agent,
                    safe_message,
                    safe_user,
                    request.session_id,
                    allowed_sources,
                    allowed_collections,
                    preferred_sources,
                ),
                timeout=_RUN_AGENT_TIMEOUT_SECONDS,
            )
            _log_step(rid, "stream_run_agent", agent_start)

            text = str(final_answer or "").strip()
            sources = state.get("sources", []) if isinstance(state, dict) else []
            sources = [str(s) for s in sources if str(s).strip()]

            if text:
                chunk_size = 6
                for i in range(0, len(text), chunk_size):
                    yield f"__CHUNK__:{text[i:i + chunk_size]}\n"
                    await asyncio.sleep(0)
            else:
                yield "__CHUNK__:Agent did not return a response.\n"
                text = "Agent did not return a response."

            save_start = time.perf_counter()
            await asyncio.to_thread(_save_chat_message, safe_user, request.session_id, "user", safe_message)
            await asyncio.to_thread(
                _save_chat_message,
                safe_user,
                request.session_id,
                "assistant",
                text,
                sources,
            )
            _log_step(rid, "stream_save_messages", save_start)

            yield "__STEP__:Done\n"
            if sources:
                yield f"__SOURCES__:{json.dumps(sources, ensure_ascii=False)}\n"

            logger.info(
                "[CHAT][%s] stream_done total_ms=%.2f msg_len=%d sources=%d",
                rid,
                _elapsed_ms(req_start),
                len(safe_message),
                len(sources),
            )
        except asyncio.TimeoutError:
            logger.warning("[CHAT][%s] stream_timeout total_ms=%.2f", rid, _elapsed_ms(req_start))
            yield "\n[ERROR] Agent timeout, please try again."
        except Exception as e:
            logger.exception("[CHAT][%s] Chat stream error total_ms=%.2f", rid, _elapsed_ms(req_start))
            yield f"\n[ERROR] Agent encountered an error: {str(e)}"

    return StreamingResponse(event_generator(), media_type="text/plain; charset=utf-8")
