import chromadb
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="./memory_db")

memory_col = client.get_or_create_collection("user_memory")

def add_memory(user_id: str, text: str):
    embedding = embedding_model.encode(text).tolist()

    memory_col.add(
        ids=[f"{user_id}-{hash(text)}"],
        documents=[text],
        embeddings=[embedding],
        metadatas=[{"user_id": user_id}]
    )

def query_memory(user_id: str, query: str, top_k: int = 5):
    q_emb = embedding_model.encode(query).tolist()

    res = memory_col.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        where={"user_id": user_id}
    )

    return res.get("documents", [[]])[0]