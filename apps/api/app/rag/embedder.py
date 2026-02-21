from functools import lru_cache
from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_MODEL

@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)

def embed_text(text: str) -> list[float]:
    model = get_model()
    vec = model.encode([text], normalize_embeddings=True)[0]
    return vec.tolist()

def embedding_dim() -> int:
    return get_model().get_sentence_embedding_dimension()
