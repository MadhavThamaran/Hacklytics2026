import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.rag.embedder import embed_text
from app.rag.vectorai_client import search_vectors

query = "my left shin hurts after running"

vec = embed_text(query)
results = search_vectors(vec, body_area="shin", top_k=5)

print(f"Query: {query}")
print(f"Results: {len(results)}")
for r in results:
    p = r.get("payload", {})
    print("-" * 40)
    print("score:", r.get("score"))
    print("title:", p.get("title"))
    print("body_area:", p.get("body_area"))
    print("goal:", p.get("goal"))
    print("dosage:", p.get("dosage"))
