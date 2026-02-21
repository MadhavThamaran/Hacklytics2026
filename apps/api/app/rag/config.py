import os

VECTORAI_ADDRESS = os.getenv("VECTORAI_ADDRESS", "localhost:50051")
VECTORAI_COLLECTION = os.getenv("VECTORAI_COLLECTION", "running_coach_exercises")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.2"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
