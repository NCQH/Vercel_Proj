from rag.retriever import retrieve
from rag.vectorstore import get_db
from rag.embedding import get_embedding

def run(question):
    db = get_db(get_embedding())
    return retrieve(db, question)