from langchain_chroma import Chroma
import chromadb
import os
import re
from src.rag.embedding import get_embedding
from src.config import CHROMA_DB_DIR, CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY

def get_chroma_client():
    if CHROMA_API_KEY:
        # Use official Chroma Cloud Client
        return chromadb.CloudClient(
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE,
            api_key=CHROMA_API_KEY
        )
    else:
        # Fallback to local
        db_dir = "/tmp/chroma_db" if os.environ.get("VERCEL") else CHROMA_DB_DIR
        return chromadb.PersistentClient(path=db_dir)

def _safe_collection_suffix(raw: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", (raw or "default").strip())
    return safe[:80] or "default"

def add_documents(vectorstore, chunks):
    vectorstore.add_documents(chunks)

def get_vectorstore(user_id: str = "default"):
    return Chroma(
        client=get_chroma_client(),
        collection_name=f"rag_docs_{_safe_collection_suffix(user_id)}",
        embedding_function=get_embedding()
    )