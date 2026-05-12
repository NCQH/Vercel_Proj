import os
import re
import uuid
import httpx
import logging
from datetime import datetime, timezone
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def _supabase_headers() -> dict:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=500, detail="Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

def _encode_eq(value: str) -> str:
    return httpx.QueryParams({"v": value})["v"]

def _safe_user_id(raw: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", (raw or "").strip())
    return safe[:80] or "unknown_user"

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

def _save_chat_message(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
    citations: list[str] | None = None,
) -> None:
    headers = _supabase_headers()
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "citations": citations or [],
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=headers, json=payload)

    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to save chat message: {response.text}")

def _get_recent_chat_history(user_id: str, session_id: str, limit: int = 8) -> list[dict]:
    headers = _supabase_headers()
    url = (
        f"{SUPABASE_URL}/rest/v1/chat_messages"
        f"?user_id=eq.{_encode_eq(user_id)}"
        f"&session_id=eq.{_encode_eq(session_id)}"
        f"&select=role,content,citations,created_at"
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

def _get_allowed_sources_and_collections(user_id: str) -> tuple[list[str], list[str]]:
    headers = _supabase_headers()
    allowed: set[str] = set()
    collections: set[str] = {user_id}

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
                collections.add(f"class_{cid}")
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

    return sorted(allowed), sorted(collections)

def _get_allowed_sources(user_id: str) -> list[str]:
    """Get list of allowed source filenames for a user (without collections)."""
    allowed_sources, _ = _get_allowed_sources_and_collections(user_id)
    return allowed_sources

def _save_upload_metadata(
    user_id: str,
    file_id: str,
    original_filename: str,
    storage_path: str,
    size_bytes: int,
) -> None:
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    payload = {
        "file_id": file_id,
        "user_id": user_id,
        "original_filename": original_filename,
        "stored_path": storage_path,
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
        f"?user_id=eq.{_encode_eq(user_id)}"
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
