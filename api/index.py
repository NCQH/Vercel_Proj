import sys
import os
import re
import uuid
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
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from dotenv import load_dotenv
import logging
import asyncio
import httpx

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: str = "web_session"


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


def _build_personalized_prompt(user_message: str, profile: dict, history: list[dict]) -> str:
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

    return (
        "You are a personalized AI teaching assistant. Use the user profile and conversation history to tailor your answer.\n\n"
        f"{profile_block}\n"
        f"Recent conversation:\n{history_block}\n\n"
        f"Current user message:\n{user_message}"
    )


@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        safe_user = _safe_user_id(request.user_id)
        profile = _get_user_profile(safe_user)
        history = _get_recent_chat_history(safe_user, request.session_id)
        enriched_message = _build_personalized_prompt(request.message, profile, history)

        response = run_agent(
            enriched_message,
            user_id=safe_user,
            session_id=request.session_id,
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


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            safe_user = _safe_user_id(request.user_id)
            profile = _get_user_profile(safe_user)
            history = _get_recent_chat_history(safe_user, request.session_id)
            enriched_message = _build_personalized_prompt(request.message, profile, history)

            reply = run_agent(
                enriched_message,
                user_id=safe_user,
                session_id=request.session_id,
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


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "LangGraph agent is running!"}
