import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.rag.embedding import get_embedding
from src.rag.vectorstore import get_vectorstore, add_documents
from src.config import CHROMA_DB_DIR, DOCUMENT_PATH, CHUNK_SIZE, CHUNK_OVERLAP
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

        print(f'Loaded {file}')

    print(f"Loaded {len(docs)} documents")

    return docs

# chunk strategy
def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunks = splitter.split_documents(documents)

    print(f"Split into {len(chunks)} chunks")

    return chunks

def ingest():
    documents = load_documents()
    chunks = chunk_documents(documents)
    vectorstore = get_vectorstore()
    add_documents(vectorstore, chunks)


