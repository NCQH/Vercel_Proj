import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DB_PATH = str(PROJECT_ROOT / "memory_db")
CONVERSATION_PATH = PROJECT_ROOT / "memory_db" / "conversation_history.jsonl"
SUMMARY_PATH = PROJECT_ROOT / "memory_db" / "session_summaries.json"

client = chromadb.PersistentClient(path=MEMORY_DB_PATH)

memory_col = client.get_or_create_collection("user_memory")


def _stable_memory_id(user_id: str, text: str) -> str:
    raw = f"{user_id}::{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def add_memory(
    user_id: str,
    text: str,
    memory_type: str = "fact",
    source: str = "user",
    confidence: float = 0.8,
    tags: Optional[List[str]] = None,
):
    embedding = embedding_model.encode(text).tolist()
    metadata = {
        "user_id": user_id,
        "memory_type": memory_type,
        "source": source,
        "confidence": float(confidence),
        "tags": ",".join(tags or []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    memory_col.upsert(
        ids=[_stable_memory_id(user_id, text)],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def query_memory(
    user_id: str,
    query: str,
    top_k: int = 5,
    max_distance: Optional[float] = None,
) -> List[str]:
    q_emb = embedding_model.encode(query).tolist()

    res = memory_col.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        where={"user_id": user_id},
        include=["documents", "distances", "metadatas"],
    )

    documents = res.get("documents", [[]])[0]
    distances = res.get("distances", [[]])[0]

    if max_distance is None:
        return documents

    filtered: List[str] = []
    for idx, doc in enumerate(documents):
        distance = distances[idx] if idx < len(distances) else None
        if distance is None or distance <= max_distance:
            filtered.append(doc)

    return filtered


def query_memory_records(
    user_id: str,
    query: str,
    top_k: int = 5,
    max_distance: Optional[float] = None,
) -> List[Dict[str, Any]]:
    q_emb = embedding_model.encode(query).tolist()

    res = memory_col.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        where={"user_id": user_id},
        include=["documents", "distances", "metadatas"],
    )

    documents = res.get("documents", [[]])[0]
    distances = res.get("distances", [[]])[0]
    metadatas = res.get("metadatas", [[]])[0]

    rows: List[Dict[str, Any]] = []
    for idx, doc in enumerate(documents):
        distance = distances[idx] if idx < len(distances) else None
        if max_distance is not None and distance is not None and distance > max_distance:
            continue

        metadata = metadatas[idx] if idx < len(metadatas) else {}
        rows.append(
            {
                "text": doc,
                "distance": distance,
                "metadata": metadata or {},
            }
        )

    return rows


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


def load_recent_conversation(user_id: str, max_turns: int = 3) -> List[Dict[str, str]]:
    if max_turns <= 0:
        return []

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
    SUMMARY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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