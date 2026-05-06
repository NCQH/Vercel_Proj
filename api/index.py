import sys
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.base_agent import run_agent
from src.rag.vectorstore import get_vectorstore, add_documents
from src.memory.memory_service import (
    load_short_term_memory,
    load_semantic_memory,
    load_long_term_memory,
    load_episodic_memory,
    load_session_context_summary,
)
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from dotenv import load_dotenv
import logging
import asyncio
import httpx
import json

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

app = FastAPI()

class RoadmapRefreshRequest(BaseModel):
    user_id: str


class RoadmapItemUpdateRequest(BaseModel):
    user_id: str
    status: str = "todo"
    progress: int | None = None


class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: str = "web_session"
    preferred_sources: list[str] = []


def _encode_eq(value: str) -> str:
    return httpx.QueryParams({"v": value})["v"]


def _save_chat_message(user_id: str, session_id: str, role: str, content: str) -> None:
    headers = _supabase_headers()
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content,
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=headers, json=payload)

    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to save chat message: {response.text}")


def _get_user_profile(user_id: str) -> dict:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/users"
        f"?id=eq.{_encode_eq(user_id)}"
        f"&select=id,email,full_name,class_name,onboarded"
        f"&limit=1"
    )

    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)

    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to load user profile: {response.text}")

    rows = response.json()
    return rows[0] if rows else {}


def _get_recent_chat_history(user_id: str, session_id: str, limit: int = 8) -> list[dict]:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/chat_messages"
        f"?user_id=eq.{_encode_eq(user_id)}"
        f"&session_id=eq.{_encode_eq(session_id)}"
        f"&select=role,content,created_at"
        f"&order=created_at.desc"
        f"&limit={limit}"
    )

    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)

    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to load chat history: {response.text}")

    rows = response.json()
    rows.reverse()
    return rows


def _list_chat_sessions(user_id: str, limit: int = 20) -> list[dict]:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/chat_messages"
        f"?user_id=eq.{_encode_eq(user_id)}"
        f"&select=session_id,role,content,created_at"
        f"&order=created_at.desc"
        f"&limit=500"
    )

    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)

    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list chat sessions: {response.text}")

    rows = response.json()
    sessions: dict[str, dict] = {}
    for row in rows:
        sid = str(row.get("session_id") or "").strip()
        if not sid or sid in sessions:
            continue
        content = str(row.get("content") or "").strip()
        preview = content[:80] + ("..." if len(content) > 80 else "")
        sessions[sid] = {
            "session_id": sid,
            "last_message": preview,
            "last_role": row.get("role") or "assistant",
            "last_created_at": row.get("created_at"),
        }
        if len(sessions) >= max(1, min(limit, 100)):
            break

    return list(sessions.values())



def _build_personalized_prompt(
    user_message: str,
    profile: dict,
    history: list[dict],
    allowed_sources: list[str] | None = None,
    preferred_sources: list[str] | None = None,
) -> str:
    profile_block = (
        f"User profile:\n"
        f"- Name: {profile.get('full_name') or 'Unknown'}\n"
        f"- Class: {profile.get('class_name') or 'Unknown'}\n"
        f"- Email: {profile.get('email') or 'Unknown'}\n"
    )

    history_lines = []
    for item in history:
        role = (item.get("role") or "unknown").upper()
        content = (item.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")

    history_block = "\n".join(history_lines) if history_lines else "No prior history."
    source_policy = ""
    if allowed_sources is not None:
        safe_sources = ", ".join(sorted(set(s for s in allowed_sources if s))) or "(none)"
        preferred = [s for s in (preferred_sources or []) if s in set(allowed_sources)]
        preferred_text = ", ".join(preferred) if preferred else "(none)"
        source_policy = (
            "\n\nAccess policy:\n"
            "- Only use/refer to materials in this allowlist of source filenames.\n"
            f"- Allowed sources: {safe_sources}\n"
            f"- Preferred sources for this question: {preferred_text}\n"
            "- If preferred sources have relevant info, prioritize them first.\n"
            "- If information appears from non-allowed source, ignore it."
        )

    return (
        "You are a personalized AI teaching assistant. Use the user profile and conversation history to tailor your answer.\n\n"
        f"{profile_block}\n"
        f"Recent conversation:\n{history_block}\n\n"
        f"Current user message:\n{user_message}"
        f"{source_policy}"
    )



def _get_allowed_sources(user_id: str) -> list[str]:
    headers = _supabase_headers()
    allowed: set[str] = set()

    # Personal uploads
    personal_url = (
        f"{SUPABASE_URL}/rest/v1/uploads"
        f"?user_id=eq.{_encode_eq(user_id)}"
        f"&select=original_filename"
    )
    with httpx.Client(timeout=15.0) as client:
        p_resp = client.get(personal_url, headers=headers)
        if p_resp.status_code < 300:
            for row in p_resp.json():
                fn = row.get("original_filename")
                if fn:
                    allowed.add(str(fn))

    # Approved class memberships -> class files
    mem_url = (
        f"{SUPABASE_URL}/rest/v1/class_members"
        f"?student_id=eq.{_encode_eq(user_id)}"
        f"&status=eq.approved"
        f"&select=class_id"
    )
    with httpx.Client(timeout=15.0) as client:
        m_resp = client.get(mem_url, headers=headers)
        if m_resp.status_code < 300:
            class_ids = [r.get("class_id") for r in m_resp.json() if r.get("class_id")]
            for cid in class_ids:
                cf_url = (
                    f"{SUPABASE_URL}/rest/v1/class_files"
                    f"?class_id=eq.{_encode_eq(str(cid))}"
                    f"&select=original_filename"
                )
                cf_resp = client.get(cf_url, headers=headers)
                if cf_resp.status_code < 300:
                    for row in cf_resp.json():
                        fn = row.get("original_filename")
                        if fn:
                            allowed.add(str(fn))

    return sorted(allowed)


@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        safe_user = _safe_user_id(request.user_id)
        profile = _get_user_profile(safe_user)
        history = _get_recent_chat_history(safe_user, request.session_id)
        allowed_sources = _get_allowed_sources(safe_user)
        preferred_sources = [s for s in (request.preferred_sources or []) if isinstance(s, str)]
        enriched_message = _build_personalized_prompt(
            request.message,
            profile,
            history,
            allowed_sources=allowed_sources,
            preferred_sources=preferred_sources,
        )

        response = run_agent(
            enriched_message,
            user_id=safe_user,
            session_id=request.session_id,
            allowed_sources=allowed_sources,
            preferred_sources=preferred_sources,
        )

        _save_chat_message(safe_user, request.session_id, "user", request.message)
        _save_chat_message(safe_user, request.session_id, "assistant", response)

        return {"reply": response}
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=f"Agent encountered an error: {str(e)}")


@app.get("/api/chat/history")
def chat_history(user_id: str = "", session_id: str = "web_session", limit: int = 30):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = _get_recent_chat_history(safe_user, session_id, limit=max(1, min(limit, 100)))
    return {"ok": True, "user_id": safe_user, "session_id": session_id, "items": items}


@app.get("/api/chat/sessions")
def chat_sessions(user_id: str = "", limit: int = 20):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = _list_chat_sessions(safe_user, limit=max(1, min(limit, 100)))
    return {"ok": True, "user_id": safe_user, "items": items}


@app.get("/api/chat/sources")
def chat_sources(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = _get_allowed_sources(safe_user)
    return {"ok": True, "user_id": safe_user, "items": items}




@app.get("/api/memory/debug")
def memory_debug(user_id: str = "", session_id: str = "web_session", query: str = "", top_k: int = 5):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    q = (query or "what should I remember about this user").strip()
    k = max(1, min(top_k, 10))

    short_term = load_short_term_memory(safe_user, session_id=session_id, max_turns=8)
    semantic = load_semantic_memory(safe_user, q, top_k=k)
    long_term = load_long_term_memory(safe_user, q, top_k=k)
    episodic = load_episodic_memory(safe_user, q, session_id=session_id, top_k=k)
    summary = load_session_context_summary(safe_user)

    return {
        "ok": True,
        "user_id": safe_user,
        "session_id": session_id,
        "query": q,
        "memory": {
            "short_term": short_term,
            "semantic": semantic,
            "long_term": long_term,
            "episodic": episodic,
            "summary": summary,
        },
    }


def _generate_roadmap_with_llm_from_behavior(user_id: str) -> list[dict]:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is required for roadmap generation")

    sessions = _list_chat_sessions(user_id, limit=10)
    all_sources = _get_allowed_sources(user_id)

    history = []
    for s in sessions[:5]:
        sid = str(s.get("session_id") or "")
        if sid:
            history.extend(_get_recent_chat_history(user_id, sid, limit=12))

    user_messages = [str(h.get("content") or "").strip() for h in history if str(h.get("role") or "") == "user"]
    assistant_messages = [str(h.get("content") or "").strip() for h in history if str(h.get("role") or "") == "assistant"]

    behavior_payload = {
        "user_id": user_id,
        "recent_sessions": [s.get("session_id") for s in sessions[:5]],
        "recent_user_messages": user_messages[-30:],
        "recent_assistant_messages": assistant_messages[-20:],
        "available_sources": all_sources[:30],
        "requirements": {
            "item_count": 4,
            "id_format": "rm-1, rm-2, ...",
            "priority_values": ["high", "medium", "low"],
            "status_default": "todo",
            "progress_range": [0, 100],
            "include_fields": ["id", "topic", "description", "priority", "eta_minutes", "progress", "status", "sources", "actions"],
            "language": "vi",
        },
    }

    llm = ChatOpenAI(model=DEFAULT_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)
    resp = llm.invoke([
        {"role": "system", "content": "You are an academic learning planner. Build a personalized roadmap strictly from user behavior evidence. Return STRICT JSON array only, no markdown."},
        {"role": "user", "content": json.dumps(behavior_payload, ensure_ascii=False)},
    ])

    raw = (resp.content or "").strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not parsed:
        raise HTTPException(status_code=500, detail="Invalid roadmap JSON generated by LLM")

    normalized = []
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            continue
        normalized.append({
            "id": str(item.get("id") or f"rm-{idx}"),
            "topic": str(item.get("topic") or f"Roadmap item {idx}"),
            "description": str(item.get("description") or ""),
            "priority": str(item.get("priority") or "medium").lower() if str(item.get("priority") or "medium").lower() in {"high", "medium", "low"} else "medium",
            "eta_minutes": max(10, min(int(item.get("eta_minutes", 30)), 240)),
            "progress": max(0, min(int(item.get("progress", 0)), 100)),
            "status": str(item.get("status") or "todo").lower() if str(item.get("status") or "todo").lower() in {"todo", "doing", "done"} else "todo",
            "sources": [str(s) for s in (item.get("sources") or []) if str(s).strip()],
            "actions": [str(a) for a in (item.get("actions") or []) if str(a).strip()][:6],
        })

    if not normalized:
        raise HTTPException(status_code=500, detail="No valid roadmap items generated")
    return normalized



def _save_roadmap_plan(user_id: str, mode: str, items: list[dict]) -> dict:
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"

    next_action = next((i for i in items if i.get("status") != "done"), items[0] if items else None)
    summary = f"Roadmap generated with {len(items)} items"
    plan_payload = {
        "user_id": user_id,
        "mode": mode,
        "summary": summary,
        "next_action_item_id": (next_action or {}).get("id"),
    }

    with httpx.Client(timeout=15.0) as client:
        plan_resp = client.post(f"{SUPABASE_URL}/rest/v1/roadmap_plans", headers=headers, json=plan_payload)
    if plan_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to save roadmap plan: {plan_resp.text}")

    plan_rows = plan_resp.json()
    if not plan_rows:
        raise HTTPException(status_code=500, detail="Roadmap plan save returned empty response")
    plan = plan_rows[0]
    plan_id = str(plan.get("id"))

    item_headers = _supabase_headers()
    item_headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    item_payloads = []
    for item in items:
        item_payloads.append({
            "plan_id": plan_id,
            "item_key": item.get("id"),
            "topic": item.get("topic"),
            "description": item.get("description"),
            "priority": item.get("priority"),
            "eta_minutes": int(item.get("eta_minutes", 30)),
            "progress": int(item.get("progress", 0)),
            "status": item.get("status", "todo"),
            "sources": item.get("sources", []),
            "actions": item.get("actions", []),
        })

    with httpx.Client(timeout=15.0) as client:
        items_resp = client.post(f"{SUPABASE_URL}/rest/v1/roadmap_items", headers=item_headers, json=item_payloads)
    if items_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to save roadmap items: {items_resp.text}")

    saved_items_rows = items_resp.json()
    saved_items = []
    for r in saved_items_rows:
        saved_items.append({
            "id": r.get("item_key"),
            "topic": r.get("topic"),
            "description": r.get("description"),
            "priority": r.get("priority"),
            "eta_minutes": r.get("eta_minutes"),
            "progress": r.get("progress"),
            "status": r.get("status"),
            "sources": r.get("sources") or [],
            "actions": r.get("actions") or [],
        })

    next_action_saved = next((i for i in saved_items if i.get("status") != "done"), saved_items[0] if saved_items else None)
    return {"plan": plan, "items": saved_items, "next_action": next_action_saved}


def _load_latest_roadmap_plan(user_id: str) -> dict | None:
    headers = _supabase_headers()
    plan_url = (
        f"{SUPABASE_URL}/rest/v1/roadmap_plans"
        f"?user_id=eq.{_encode_eq(user_id)}"
        f"&select=id,user_id,mode,summary,next_action_item_id,generated_at,updated_at"
        f"&order=generated_at.desc"
        f"&limit=1"
    )

    with httpx.Client(timeout=15.0) as client:
        plan_resp = client.get(plan_url, headers=headers)
    if plan_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to load roadmap plan: {plan_resp.text}")
    plan_rows = plan_resp.json()
    if not plan_rows:
        return None

    plan = plan_rows[0]
    plan_id = str(plan.get("id"))
    items_url = (
        f"{SUPABASE_URL}/rest/v1/roadmap_items"
        f"?plan_id=eq.{_encode_eq(plan_id)}"
        f"&select=item_key,topic,description,priority,eta_minutes,progress,status,sources,actions,updated_at"
        f"&order=updated_at.asc"
    )
    with httpx.Client(timeout=15.0) as client:
        items_resp = client.get(items_url, headers=headers)
    if items_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to load roadmap items: {items_resp.text}")

    item_rows = items_resp.json()
    items = [
        {
            "id": r.get("item_key"),
            "topic": r.get("topic"),
            "description": r.get("description"),
            "priority": r.get("priority"),
            "eta_minutes": r.get("eta_minutes"),
            "progress": r.get("progress"),
            "status": r.get("status"),
            "sources": r.get("sources") or [],
            "actions": r.get("actions") or [],
        }
        for r in item_rows
    ]
    next_action = next((i for i in items if i.get("status") != "done"), items[0] if items else None)
    return {"plan": plan, "items": items, "next_action": next_action}


def _update_roadmap_item_db(user_id: str, item_id: str, status: str, progress: int | None = None) -> dict:
    latest = _load_latest_roadmap_plan(user_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No roadmap plan found for user")

    plan_id = str((latest.get("plan") or {}).get("id") or "")
    if not plan_id:
        raise HTTPException(status_code=404, detail="Invalid roadmap plan")

    payload = {"status": status}
    if progress is not None:
        payload["progress"] = max(0, min(int(progress), 100))

    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    patch_url = (
        f"{SUPABASE_URL}/rest/v1/roadmap_items"
        f"?plan_id=eq.{_encode_eq(plan_id)}"
        f"&item_key=eq.{_encode_eq(item_id)}"
    )
    with httpx.Client(timeout=15.0) as client:
        patch_resp = client.patch(patch_url, headers=headers, json=payload)
    if patch_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to update roadmap item: {patch_resp.text}")

    rows = patch_resp.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Roadmap item not found")

    row = rows[0]
    return {
        "id": row.get("item_key"),
        "status": row.get("status"),
        "progress": row.get("progress"),
    }



@app.get("/api/roadmap")
def get_roadmap(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)

    latest = _load_latest_roadmap_plan(safe_user)
    if latest:
        plan = latest.get("plan") or {}
        return {
            "ok": True,
            "user_id": safe_user,
            "mode": plan.get("mode") or "v2",
            "next_action": latest.get("next_action"),
            "items": latest.get("items") or [],
        }

    items = _generate_roadmap_with_llm_from_behavior(safe_user)
    saved = _save_roadmap_plan(safe_user, "v2", items)

    return {
        "ok": True,
        "user_id": safe_user,
        "mode": "v2",
        "next_action": saved.get("next_action"),
        "items": saved.get("items") or [],
    }


@app.post("/api/roadmap/refresh")
def refresh_roadmap(payload: RoadmapRefreshRequest):
    safe_user = _safe_user_id(payload.user_id)
    items = _generate_roadmap_with_llm_from_behavior(safe_user)
    saved = _save_roadmap_plan(safe_user, "v2", items)
    return {
        "ok": True,
        "user_id": safe_user,
        "mode": "v2",
        "next_action": saved.get("next_action"),
        "items": saved.get("items") or [],
    }


@app.patch("/api/roadmap/items/{item_id}")
def update_roadmap_item(item_id: str, payload: RoadmapItemUpdateRequest):
    safe_user = _safe_user_id(payload.user_id)
    status = (payload.status or "todo").strip().lower()
    if status not in {"todo", "doing", "done"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    updated = _update_roadmap_item_db(safe_user, item_id, status, payload.progress)
    return {
        "ok": True,
        "user_id": safe_user,
        "item_id": updated.get("id"),
        "status": updated.get("status"),
        "progress": updated.get("progress"),
    }




@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            safe_user = _safe_user_id(request.user_id)
            profile = _get_user_profile(safe_user)
            history = _get_recent_chat_history(safe_user, request.session_id)
            allowed_sources = _get_allowed_sources(safe_user)
            preferred_sources = [s for s in (request.preferred_sources or []) if isinstance(s, str)]
            enriched_message = _build_personalized_prompt(
                request.message,
                profile,
                history,
                allowed_sources=allowed_sources,
                preferred_sources=preferred_sources,
            )

            reply = run_agent(
                enriched_message,
                user_id=safe_user,
                session_id=request.session_id,
                allowed_sources=allowed_sources,
                preferred_sources=preferred_sources,
            )
            text = reply or ""

            _save_chat_message(safe_user, request.session_id, "user", request.message)
            _save_chat_message(safe_user, request.session_id, "assistant", text)

            # Chunk by words for smoother progressive rendering on the client.
            words = text.split(" ")
            for i, word in enumerate(words):
                chunk = (word + " ") if i < len(words) - 1 else word
                yield chunk
                await asyncio.sleep(0.015)
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"\n[ERROR] Agent encountered an error: {str(e)}"

    return StreamingResponse(event_generator(), media_type="text/plain; charset=utf-8")


def _safe_user_id(raw: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", (raw or "").strip())
    return safe[:80] or "unknown_user"


def _safe_filename(raw: str) -> str:
    name = Path(raw or "upload.bin").name
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:180] or "upload.bin"


def _supabase_headers() -> dict:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=500, detail="Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def _save_upload_metadata(
    user_id: str,
    file_id: str,
    original_filename: str,
    stored_path: str,
    size_bytes: int,
) -> None:
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    payload = {
        "file_id": file_id,
        "user_id": user_id,
        "original_filename": original_filename,
        "stored_path": stored_path,
        "size_bytes": size_bytes,
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.post(f"{SUPABASE_URL}/rest/v1/uploads", headers=headers, json=payload)

    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to save upload metadata: {response.text}")


def _list_upload_metadata(user_id: str):
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/uploads"
        f"?user_id=eq.{httpx.QueryParams({'v': user_id})['v']}"
        f"&select=file_id,original_filename,stored_path,size_bytes,uploaded_at"
        f"&order=uploaded_at.desc"
    )

    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)

    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list uploads: {response.text}")

    rows = response.json()
    return [
        {
            "file_id": row.get("file_id"),
            "filename": row.get("original_filename"),
            "path": row.get("stored_path"),
            "size": row.get("size_bytes"),
            "uploaded_at": row.get("uploaded_at"),
        }
        for row in rows
    ]


@app.get("/api/uploads")
def list_uploads(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    items = _list_upload_metadata(safe_user)
    return {"ok": True, "user_id": safe_user, "items": items}


def _create_class(lecturer_id: str, name: str, description: str = "") -> dict:
    code = uuid.uuid4().hex[:8].upper()
    payload = {
        "lecturer_id": lecturer_id,
        "name": name.strip(),
        "description": description.strip(),
        "code": code,
    }
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(f"{SUPABASE_URL}/rest/v1/classes", headers=headers, json=payload)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to create class: {response.text}")
    rows = response.json()
    return rows[0] if rows else payload


def _list_classes_for_lecturer(lecturer_id: str) -> list[dict]:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/classes"
        f"?lecturer_id=eq.{_encode_eq(lecturer_id)}"
        f"&select=id,name,code,description,is_active,created_at"
        f"&order=created_at.desc"
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list lecturer classes: {response.text}")
    return response.json()


def _list_classes_for_student(student_id: str) -> list[dict]:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/class_members"
        f"?student_id=eq.{_encode_eq(student_id)}"
        f"&select=id,status,requested_at,approved_at,class_id,classes(id,name,code,description,is_active,lecturer_id)"
        f"&order=requested_at.desc"
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list student classes: {response.text}")
    rows = response.json()
    out = []
    for row in rows:
        cls = (row.get("classes") or {})
        out.append({
            "membership_id": row.get("id"),
            "status": row.get("status"),
            "requested_at": row.get("requested_at"),
            "approved_at": row.get("approved_at"),
            "class": cls,
        })
    return out


def _list_public_classes() -> list[dict]:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/classes"
        f"?is_active=eq.true"
        f"&select=id,name,code,description,lecturer_id,created_at"
        f"&order=created_at.desc"
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list public classes: {response.text}")
    return response.json()


def _list_pending_requests_for_lecturer(lecturer_id: str, class_id: str = "") -> list[dict]:
    classes = _list_classes_for_lecturer(lecturer_id)
    owned_ids = {c.get("id") for c in classes}
    if class_id:
        if class_id not in owned_ids:
            raise HTTPException(status_code=403, detail="You are not owner of this class")
        owned_ids = {class_id}
    if not owned_ids:
        return []

    headers = _supabase_headers()
    out: list[dict] = []
    with httpx.Client(timeout=15.0) as client:
        for cid in owned_ids:
            url = (
                f"{SUPABASE_URL}/rest/v1/class_members"
                f"?class_id=eq.{_encode_eq(str(cid))}"
                f"&status=eq.pending"
                f"&select=id,class_id,student_id,status,requested_at"
                f"&order=requested_at.asc"
            )
            response = client.get(url, headers=headers)
            if response.status_code >= 300:
                raise HTTPException(status_code=500, detail=f"Failed to list pending requests: {response.text}")
            out.extend(response.json())
    return out


def _ensure_lecturer_class_owner(lecturer_id: str, class_id: str) -> None:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/classes"
        f"?id=eq.{_encode_eq(class_id)}"
        f"&lecturer_id=eq.{_encode_eq(lecturer_id)}"
        f"&select=id&limit=1"
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed class ownership check: {response.text}")
    if not response.json():
        raise HTTPException(status_code=403, detail="You are not owner of this class")


def _is_student_approved_in_class(student_id: str, class_id: str) -> bool:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/class_members"
        f"?student_id=eq.{_encode_eq(student_id)}"
        f"&class_id=eq.{_encode_eq(class_id)}"
        f"&status=eq.approved"
        f"&select=id&limit=1"
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        return False
    return bool(response.json())


@app.get("/api/classes")
def list_classes(user_id: str = "", role: str = "student"):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    if role == "lecturer":
        items = _list_classes_for_lecturer(safe_user)
    else:
        items = _list_classes_for_student(safe_user)
    return {"ok": True, "items": items}


@app.get("/api/classes/public")
def list_public_classes(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    _ = _safe_user_id(user_id)
    return {"ok": True, "items": _list_public_classes()}


@app.get("/api/classes/pending")
def list_pending_requests(user_id: str = "", class_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    items = _list_pending_requests_for_lecturer(safe_user, class_id=class_id)
    return {"ok": True, "items": items}


@app.post("/api/classes")
def create_class(user_id: str = Form(""), name: str = Form(""), description: str = Form("")):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    if not name.strip():
        raise HTTPException(status_code=400, detail="Missing class name")
    safe_user = _safe_user_id(user_id)
    cls = _create_class(safe_user, name, description)
    return {"ok": True, "class": cls}


@app.patch("/api/classes/{class_id}")
def update_class(class_id: str, user_id: str = Form(""), name: str = Form(""), description: str = Form(""), is_active: str = Form("true")):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    _ensure_lecturer_class_owner(safe_user, class_id)

    payload = {
        "name": name.strip(),
        "description": description.strip(),
        "is_active": is_active.lower() == "true",
    }
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    url = f"{SUPABASE_URL}/rest/v1/classes?id=eq.{_encode_eq(class_id)}"
    with httpx.Client(timeout=15.0) as client:
        response = client.patch(url, headers=headers, json=payload)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to update class: {response.text}")
    rows = response.json()
    return {"ok": True, "class": rows[0] if rows else payload}


@app.post("/api/classes/join")
def request_join_class(user_id: str = Form(""), class_code: str = Form("")):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    if not class_code.strip():
        raise HTTPException(status_code=400, detail="Missing class code")

    safe_user = _safe_user_id(user_id)
    headers = _supabase_headers()
    class_url = (
        f"{SUPABASE_URL}/rest/v1/classes"
        f"?code=eq.{_encode_eq(class_code.strip().upper())}"
        f"&select=id,name,code,lecturer_id&limit=1"
    )
    with httpx.Client(timeout=15.0) as client:
        class_resp = client.get(class_url, headers=headers)
    if class_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to find class: {class_resp.text}")
    class_rows = class_resp.json()
    if not class_rows:
        raise HTTPException(status_code=404, detail="Class code not found")
    cls = class_rows[0]

    payload = {
        "class_id": cls["id"],
        "student_id": safe_user,
        "status": "pending",
    }
    insert_headers = _supabase_headers()
    insert_headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(f"{SUPABASE_URL}/rest/v1/class_members", headers=insert_headers, json=payload)
    if resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to request join: {resp.text}")
    rows = resp.json()
    return {"ok": True, "membership": rows[0] if rows else payload, "class": cls}


@app.post("/api/classes/members/{membership_id}/approve")
def approve_member(membership_id: str, user_id: str = Form(""), approve: str = Form("true")):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)

    headers = _supabase_headers()
    membership_url = (
        f"{SUPABASE_URL}/rest/v1/class_members"
        f"?id=eq.{_encode_eq(membership_id)}"
        f"&select=id,class_id,student_id,status&limit=1"
    )
    with httpx.Client(timeout=15.0) as client:
        m_resp = client.get(membership_url, headers=headers)
    if m_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to load membership: {m_resp.text}")
    rows = m_resp.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Membership not found")
    membership = rows[0]

    _ensure_lecturer_class_owner(safe_user, membership["class_id"])

    payload = {
        "status": "approved" if approve.lower() == "true" else "rejected",
        "approved_by": safe_user,
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    patch_headers = _supabase_headers()
    patch_headers["Prefer"] = "return=representation"
    patch_url = f"{SUPABASE_URL}/rest/v1/class_members?id=eq.{_encode_eq(membership_id)}"
    with httpx.Client(timeout=15.0) as client:
        p_resp = client.patch(patch_url, headers=patch_headers, json=payload)
    if p_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to update membership: {p_resp.text}")
    p_rows = p_resp.json()
    return {"ok": True, "membership": p_rows[0] if p_rows else payload}


@app.get("/api/class-files")
def list_class_files(user_id: str = "", class_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    if not class_id:
        raise HTTPException(status_code=400, detail="Missing class_id")
    safe_user = _safe_user_id(user_id)

    can_access = False
    try:
        _ensure_lecturer_class_owner(safe_user, class_id)
        can_access = True
    except HTTPException:
        can_access = _is_student_approved_in_class(safe_user, class_id)

    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")

    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/class_files"
        f"?class_id=eq.{_encode_eq(class_id)}"
        f"&select=file_id,class_id,uploader_id,original_filename,stored_path,size_bytes,uploaded_at"
        f"&order=uploaded_at.desc"
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list class files: {response.text}")

    rows = response.json()
    return {"ok": True, "items": rows}


@app.post("/api/class-files/upload")
async def upload_class_file(file: UploadFile = File(...), user_id: str = Form(""), class_id: str = Form("")):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    if not class_id:
        raise HTTPException(status_code=400, detail="Missing class_id")

    safe_user = _safe_user_id(user_id)
    _ensure_lecturer_class_owner(safe_user, class_id)

    safe_name = _safe_filename(file.filename or "upload.bin")
    file_id = str(uuid.uuid4())
    class_dir = Path("data/uploads/classes") / class_id
    class_dir.mkdir(parents=True, exist_ok=True)

    target_path = class_dir / f"{file_id}_{safe_name}"
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    target_path.write_bytes(content)

    try:
        ext = target_path.suffix.lower()
        if ext == ".pdf":
            docs = PyMuPDFLoader(str(target_path)).load()
        elif ext in {".txt", ".md"}:
            docs = TextLoader(str(target_path), encoding="utf-8").load()
        else:
            docs = []

        if docs:
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
            chunks = splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata = {
                    **(chunk.metadata or {}),
                    "class_id": class_id,
                    "source": safe_name,
                    "stored_path": str(target_path),
                }
            vectorstore = get_vectorstore(user_id=f"class_{class_id}")
            add_documents(vectorstore, chunks)
    except Exception as e:
        logger.exception("Class file ingest failed")
        raise HTTPException(status_code=500, detail=f"Upload saved but RAG ingest failed: {str(e)}")

    payload = {
        "file_id": file_id,
        "class_id": class_id,
        "uploader_id": safe_user,
        "original_filename": safe_name,
        "stored_path": str(target_path),
        "size_bytes": len(content),
    }
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(f"{SUPABASE_URL}/rest/v1/class_files", headers=headers, json=payload)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to save class file metadata: {response.text}")

    rows = response.json()
    return {"ok": True, "item": rows[0] if rows else payload}


@app.get("/api/class-files/download")
def download_class_file(file_id: str = "", user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Missing file_id")

    safe_user = _safe_user_id(user_id)
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/class_files"
        f"?file_id=eq.{_encode_eq(file_id)}"
        f"&select=file_id,class_id,original_filename,stored_path,uploader_id&limit=1"
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to fetch class file: {response.text}")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=404, detail="File not found")

    item = rows[0]
    class_id = item.get("class_id")
    can_access = False
    try:
        _ensure_lecturer_class_owner(safe_user, class_id)
        can_access = True
    except HTTPException:
        can_access = _is_student_approved_in_class(safe_user, class_id)

    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")

    stored_path = Path(str(item.get("stored_path") or "")).resolve()
    if not stored_path.exists() or not stored_path.is_file():
        raise HTTPException(status_code=404, detail="Stored file missing")

    from fastapi.responses import FileResponse

    return FileResponse(
        path=str(stored_path),
        filename=str(item.get("original_filename") or stored_path.name),
        media_type="application/octet-stream",
    )


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), user_id: str = Form("")):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    safe_name = _safe_filename(file.filename or "upload.bin")
    file_id = str(uuid.uuid4())

    user_dir = Path("data/uploads") / safe_user
    user_dir.mkdir(parents=True, exist_ok=True)

    target_path = user_dir / f"{file_id}_{safe_name}"
    content = await file.read()

    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    target_path.write_bytes(content)

    # Ingest uploaded file into user-scoped RAG collection
    try:
        ext = target_path.suffix.lower()
        if ext == ".pdf":
            docs = PyMuPDFLoader(str(target_path)).load()
        elif ext in {".txt", ".md"}:
            docs = TextLoader(str(target_path), encoding="utf-8").load()
        else:
            docs = []

        if docs:
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
            chunks = splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata = {
                    **(chunk.metadata or {}),
                    "user_id": safe_user,
                    "source": safe_name,
                    "stored_path": str(target_path),
                }

            vectorstore = get_vectorstore(user_id=safe_user)
            add_documents(vectorstore, chunks)
    except Exception as e:
        logger.exception("RAG ingest failed for uploaded file")
        raise HTTPException(status_code=500, detail=f"Upload saved but RAG ingest failed: {str(e)}")
    _save_upload_metadata(
        user_id=safe_user,
        file_id=file_id,
        original_filename=safe_name,
        stored_path=str(target_path),
        size_bytes=len(content),
    )

    return {
        "ok": True,
        "file_id": file_id,
        "user_id": safe_user,
        "filename": safe_name,
        "size": len(content),
        "path": str(target_path),
    }


@app.get("/api/uploads/download")
def download_upload(file_id: str = "", user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Missing file_id")

    safe_user = _safe_user_id(user_id)
    items = _list_upload_metadata(safe_user)
    target = next((item for item in items if item.get("file_id") == file_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="File not found")

    stored_path = Path(str(target.get("path") or "")).resolve()
    if not stored_path.exists() or not stored_path.is_file():
        raise HTTPException(status_code=404, detail="Stored file missing")

    user_root = (Path("data/uploads") / safe_user).resolve()
    try:
        stored_path.relative_to(user_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    from fastapi.responses import FileResponse

    return FileResponse(
        path=str(stored_path),
        filename=str(target.get("filename") or stored_path.name),
        media_type="application/octet-stream",
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "LangGraph agent is running!"}

