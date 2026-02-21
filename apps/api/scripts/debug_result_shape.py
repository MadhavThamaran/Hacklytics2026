import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.rag.embedder import embed_text
from cortex import CortexClient

vec = embed_text("my left shin hurts after running")

with CortexClient("localhost:50051") as client:
    results = client.search("running_coach_exercises", query=vec, top_k=3)

print("num results:", len(results))
if results:
    r = results[0]
    print("type:", type(r))
    print("dir:", [x for x in dir(r) if not x.startswith("_")])
    print("repr:", r)
    for attr in ["id", "score", "payload", "metadata", "fields", "document", "data"]:
        try:
            print(f"{attr} ->", getattr(r, attr))
        except Exception as e:
            print(f"{attr} -> ERROR: {e}")
