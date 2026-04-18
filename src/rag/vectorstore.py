from langchain_chroma import Chroma
from src.rag.embedding import get_embedding
from src.config import CHROMA_DB_DIR

def add_documents(vectorstore, chunks):
    vectorstore.add_documents(chunks)

def get_vectorstore():
    return Chroma(
        collection_name="rag_docs",
        persist_directory=CHROMA_DB_DIR,
        embedding_function=get_embedding()
    )