import os
import sys
import logging
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Response
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

# Ensure the root directory is in sys.path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes import chat, roadmap, uploads, classes
from api.lib.supabase import _safe_user_id, close_supabase_client, _supabase_cache_stats
from api.lib.storage import storage_client
from api.lib.async_http import close_async_client

from src.memory.memory_service import (
    load_short_term_memory,
    load_semantic_memory,
    load_long_term_memory,
    load_episodic_memory,
    load_session_context_summary,
)

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Teaching Assistant API")
app.add_middleware(GZipMiddleware, minimum_size=500)

# Include Routers
app.include_router(chat.router)
app.include_router(roadmap.router)
app.include_router(uploads.router)
app.include_router(classes.router)


@app.on_event("shutdown")
async def shutdown_clients() -> None:
    """Close shared HTTP clients to avoid leaked sockets on shutdown."""
    await close_async_client()
    close_supabase_client()


# For backward compatibility with old frontend endpoints
@app.post("/api/upload")
async def legacy_upload(file: UploadFile = File(...), user_id: str = Form("")):
    # Maps /api/upload -> uploads.upload_file
    return await uploads.upload_file(file, user_id)


@app.get("/api/class-files")
async def legacy_list_class_files(user_id: str = "", class_id: str = ""):
    # Maps /api/class-files -> classes.list_files
    return classes.list_files(user_id, class_id)


@app.post("/api/class-files/upload")
async def legacy_upload_class_file(file: UploadFile = File(...), user_id: str = Form(""), class_id: str = Form("")):
    # Maps /api/class-files/upload -> classes.upload_class_file
    return await classes.upload_class_file(file, user_id, class_id)


@app.get("/api/class-files/download")
async def legacy_download_class_file(file_id: str = "", user_id: str = ""):
    # Maps /api/class-files/download -> classes.download_class_file_route
    return classes.download_class_file_route(file_id, user_id)


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


@app.get("/api/perf/cache-stats")
def perf_cache_stats():
    return {"ok": True, "cache": _supabase_cache_stats()}


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "AI Teaching Assistant Backend is running!"}
