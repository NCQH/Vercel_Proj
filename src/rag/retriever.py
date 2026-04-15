from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from src.config import VECTOR_DB_PATH


def get_retriever():

    embeddings = OpenAIEmbeddings()

    db = FAISS.load_local(
        VECTOR_DB_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return db.as_retriever(search_kwargs={"k": 4})