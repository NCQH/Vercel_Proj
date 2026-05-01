import os
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from src.rag.embedding import get_embedding
from src.config import (
    MEMORY_MIN_SCORE,
    MEMORY_RECENCY_DECAY_DAYS,
)

embedding_model = get_embedding()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("VERCEL"):
    MEMORY_DB_PATH = "/tmp/memory_db"
else:
    MEMORY_DB_PATH = str(PROJECT_ROOT / "memory_db")

CONVERSATION_PATH = Path(MEMORY_DB_PATH) / "conversation_history.jsonl"
SUMMARY_PATH = Path(MEMORY_DB_PATH) / "session_summaries.json"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

from src.rag.vectorstore import get_chroma_client
client = get_chroma_client()

memory_col = client.get_or_create_collection("user_memory")


def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY or "",
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY or ''}",
        "Content-Type": "application/json",
    }


def _stable_memory_id(user_id: str, text: str, memory_type: str = "long_term", session_id: str = "global") -> str:
    raw = f"{user_id}::{memory_type}::{session_id}::{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _freshness_score(created_at: str) -> float:
    dt = _parse_iso_datetime(created_at)
    if not dt:
        return 0.5
    age_days = max((datetime.now(timezone.utc) - dt).total_seconds() / 86400.0, 0.0)
    return 1.0 / (1.0 + (age_days / max(MEMORY_RECENCY_DECAY_DAYS, 1.0)))


def get_emb(text: str) -> List[float]:
    if hasattr(embedding_model, "embed_query"):
        return embedding_model.embed_query(text)
    return embedding_model.encode(text).tolist()


def add_memory(
    user_id: str,
    text: str,
    memory_type: str = "long_term",
    source: str = "user",
    confidence: float = 0.8,
    tags: Optional[List[str]] = None,
    session_id: str = "global",
    importance: float = 0.5,
) -> None:
    embedding = get_emb(text)
    now_iso = datetime.now(timezone.utc).isoformat()
    metadata = {
        "user_id": user_id,
        "memory_type": memory_type,
        "source": source,
        "confidence": float(confidence),
        "importance": float(importance),
        "session_id": session_id,
        "tags": ",".join(tags or []),
        "created_at": now_iso,
        "last_accessed_at": now_iso,
    }

    memory_col.upsert(
        ids=[_stable_memory_id(user_id, text, memory_type=memory_type, session_id=session_id)],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def query_memory_records(
    user_id: str,
    query: str,
    top_k: int = 5,
    max_distance: Optional[float] = None,
    memory_types: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q_emb = get_emb(query)

    where: Dict[str, Any]
    clauses: List[Dict[str, Any]] = [{"user_id": user_id}]
    if memory_types:
        if len(memory_types) == 1:
            clauses.append({"memory_type": memory_types[0]})
        else:
            clauses.append({"memory_type": {"$in": memory_types}})

    if len(clauses) == 1:
        where = clauses[0]
    else:
        where = {"$and": clauses}

    res = memory_col.query(
        query_embeddings=[q_emb],
        n_results=max(top_k * 3, top_k),
        where=where,
        include=["documents", "distances", "metadatas"],
    )

    documents = res.get("documents", [[]])[0]
    distances = res.get("distances", [[]])[0]
    metadatas = res.get("metadatas", [[]])[0]

    rows: List[Dict[str, Any]] = []
    for idx, doc in enumerate(documents):
        distance = distances[idx] if idx < len(distances) else None
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        if not metadata:
            continue

        if memory_types and metadata.get("memory_type") not in memory_types:
            continue
        if session_id and metadata.get("session_id") not in (session_id, "global", None):
            continue
        if max_distance is not None and distance is not None and distance > max_distance:
            continue

        confidence = float(metadata.get("confidence", 0.5))
        importance = float(metadata.get("importance", 0.5))
        freshness = _freshness_score(str(metadata.get("created_at", "")))
        similarity = 1.0 / (1.0 + (float(distance) if distance is not None else 1.0))
        score = (0.45 * similarity) + (0.25 * confidence) + (0.20 * freshness) + (0.10 * importance)

        if score < MEMORY_MIN_SCORE:
            continue

        rows.append({
            "text": doc,
            "distance": distance,
            "score": score,
            "metadata": metadata,
        })

    rows.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return rows[:top_k]


def query_memory(
    user_id: str,
    query: str,
    top_k: int = 5,
    max_distance: Optional[float] = None,
    memory_types: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> List[str]:
    rows = query_memory_records(
        user_id,
        query,
        top_k=top_k,
        max_distance=max_distance,
        memory_types=memory_types,
        session_id=session_id,
    )
    return [r.get("text", "") for r in rows if r.get("text")]


def append_conversation_turn(
    user_id: str,
    user_text: str,
    assistant_text: str,
    session_id: str = "default",
) -> None:
    CONVERSATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": user_text,
        "assistant": assistant_text,
    }
    with CONVERSATION_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _load_recent_conversation_supabase(user_id: str, session_id: str, max_turns: int) -> List[Dict[str, str]]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return []

    limit = max(2, max_turns * 2)
    url = (
        f"{SUPABASE_URL}/rest/v1/chat_messages"
        f"?user_id=eq.{httpx.QueryParams({'v': user_id})['v']}"
        f"&session_id=eq.{httpx.QueryParams({'v': session_id})['v']}"
        f"&select=role,content,created_at"
        f"&order=created_at.desc"
        f"&limit={limit}"
    )

    with httpx.Client(timeout=12.0) as client_http:
        resp = client_http.get(url, headers=_supabase_headers())
    if resp.status_code >= 300:
        return []

    rows = resp.json()
    rows.reverse()
    out: List[Dict[str, str]] = []
    for r in rows:
        role = r.get("role")
        content = (r.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out[-(max_turns * 2):]


def load_recent_conversation(user_id: str, max_turns: int = 3, session_id: str = "default") -> List[Dict[str, str]]:
    if max_turns <= 0:
        return []

    supa_rows = _load_recent_conversation_supabase(user_id, session_id=session_id, max_turns=max_turns)
    if supa_rows:
        return supa_rows

    if not CONVERSATION_PATH.exists():
        return []

    turns = []
    with CONVERSATION_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            if item.get("user_id") != user_id:
                continue
            if item.get("session_id") != session_id:
                continue
            turns.append(item)

    turns = turns[-max_turns:]
    messages: List[Dict[str, str]] = []
    for turn in turns:
        user_text = (turn.get("user") or "").strip()
        assistant_text = (turn.get("assistant") or "").strip()
        if user_text:
            messages.append({"role": "user", "content": user_text})
        if assistant_text:
            messages.append({"role": "assistant", "content": assistant_text})
    return messages


def _load_summary_map() -> Dict[str, Any]:
    if not SUMMARY_PATH.exists():
        return {}
    try:
        return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_summary_map(data: Dict[str, Any]) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session_summary(user_id: str) -> str:
    data = _load_summary_map()
    item = data.get(user_id, {})
    return (item.get("summary") or "").strip()


def save_session_summary(user_id: str, summary: str) -> None:
    data = _load_summary_map()
    data[user_id] = {
        "summary": summary,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_summary_map(data)