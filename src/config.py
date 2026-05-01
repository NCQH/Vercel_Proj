import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DOCUMENT_PATH = "data/documents"
CHROMA_DB_DIR = "chroma_db"
CHROMA_TENANT = os.getenv("CHROMA_TENANT", "default_tenant")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "default_database")
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")

CHUNK_SIZE = 400       # tokens (estimated as chars / 4)
CHUNK_OVERLAP = 80
TOP_K_SEARCH = 10
TOP_K_SELECT = 3

# Memory system knobs
MEMORY_CONTEXT_TURNS = int(os.getenv("MEMORY_CONTEXT_TURNS", "8"))
MEMORY_FACT_TOP_K = int(os.getenv("MEMORY_FACT_TOP_K", "5"))
MEMORY_FACT_MAX_DISTANCE = float(os.getenv("MEMORY_FACT_MAX_DISTANCE", "1.1"))
MEMORY_SUMMARY_TURNS = int(os.getenv("MEMORY_SUMMARY_TURNS", "16"))
MEMORY_SUMMARY_MODEL = os.getenv("MEMORY_SUMMARY_MODEL", DEFAULT_MODEL)

# New typed memory caps
MEMORY_SEMANTIC_TOP_K = int(os.getenv("MEMORY_SEMANTIC_TOP_K", "5"))
MEMORY_LONG_TERM_TOP_K = int(os.getenv("MEMORY_LONG_TERM_TOP_K", "4"))
MEMORY_EPISODIC_TOP_K = int(os.getenv("MEMORY_EPISODIC_TOP_K", "3"))
MEMORY_EPISODIC_WINDOW = int(os.getenv("MEMORY_EPISODIC_WINDOW", "20"))

# Ranking controls
MEMORY_RECENCY_DECAY_DAYS = float(os.getenv("MEMORY_RECENCY_DECAY_DAYS", "30"))
MEMORY_MIN_SCORE = float(os.getenv("MEMORY_MIN_SCORE", "0.2"))
MEMORY_LONG_TERM_TTL_DAYS = int(os.getenv("MEMORY_LONG_TERM_TTL_DAYS", "365"))
MEMORY_SEMANTIC_TTL_DAYS = int(os.getenv("MEMORY_SEMANTIC_TTL_DAYS", "365"))
MEMORY_EPISODIC_TTL_DAYS = int(os.getenv("MEMORY_EPISODIC_TTL_DAYS", "180"))