from langchain_openai import OpenAIEmbeddings
from sentence_transformers import SentenceTransformer

def get_embedding():
    try:
        # Try to use OpenAIEmbeddings first
        embedding_model = OpenAIEmbeddings()
        # Test if it works by embedding a sample text
        embedding_model.embed_query("test")
        print("Using OpenAIEmbeddings for embedding.")
        return embedding_model
    except Exception as e:
        print(f"Error occurred while initializing OpenAIEmbeddings: {e}")
        # Fallback to SentenceTransformer
        print("Falling back to SentenceTransformer.")
        return SentenceTransformer('all-MiniLM-L6-v2')