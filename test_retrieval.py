import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.rag.retriever import retrieve_dense
from dotenv import load_dotenv

load_dotenv()

# We need the user email to find the vector store. Let's look at sqlite db or something?
# Actually, just search all collections.
import chromadb
from src.config import CHROMA_DB_DIR

client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
for col in client.list_collections():
    print("Collection:", col.name)
    print("Count:", col.count())

