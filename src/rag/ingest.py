import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from src.config import VECTOR_DB_PATH, DOCUMENT_PATH


from langchain_community.document_loaders import PyMuPDFLoader, TextLoader


def load_documents():
    docs = []

    for file in os.listdir(DOCUMENT_PATH):
        path = os.path.join(DOCUMENT_PATH, file)

        if file.endswith(".pdf"):
            loader = PyMuPDFLoader(path)
            docs.extend(loader.load())

        elif file.endswith(".md") or file.endswith(".txt"):
            loader = TextLoader(path, encoding="utf-8")
            docs.extend(loader.load())

    print(f"Loaded {len(docs)} documents")

    return docs


def build_vectorstore():

    documents = load_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings()

    db = FAISS.from_documents(chunks, embeddings)

    db.save_local(VECTOR_DB_PATH)


if __name__ == "__main__":
    build_vectorstore()