from langchain_chroma import Chroma
import chromadb
import os
from src.rag.embedding import get_embedding
from src.config import CHROMA_DB_DIR, CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY

def get_chroma_client():
    if CHROMA_API_KEY:
        # Use official Chroma Cloud Client
        return chromadb.CloudClient(
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE,
            cloud_credentials=CHROMA_API_KEY
        )
    else:
        # Fallback to local
        db_dir = "/tmp/chroma_db" if os.environ.get("VERCEL") else CHROMA_DB_DIR
        return chromadb.PersistentClient(path=db_dir)

def add_documents(vectorstore, chunks):
    vectorstore.add_documents(chunks)

def get_vectorstore():
    return Chroma(
        client=get_chroma_client(),
        collection_name="rag_docs",
        embedding_function=get_embedding()
    )