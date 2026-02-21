import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from cortex import CortexClient, DistanceMetric

# Make sure "app" imports work when running as a script
API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.rag.config import VECTORAI_ADDRESS, VECTORAI_COLLECTION
from app.rag.embedder import get_model


def build_text(ex):
    instructions = ex.get("instructions", [])
    if isinstance(instructions, list):
        instructions_text = " ".join(instructions)
    else:
        instructions_text = str(instructions)

    parts = [
        ex.get("title", ""),
        ex.get("body_area", ""),
        ex.get("goal", ""),
        ex.get("when", ""),
        instructions_text,
        ex.get("dosage", ""),
        ex.get("cautions", ""),
    ]
    return " | ".join([p for p in parts if p])


def main():
    load_dotenv()

    repo_root = Path(__file__).resolve().parents[3]
    data_path = repo_root / "data" / "exercises" / "exercises.json"

    if not data_path.exists():
        raise FileNotFoundError(f"Could not find {data_path}")

    exercises = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(exercises, list) or len(exercises) == 0:
        raise ValueError("exercises.json must be a non-empty JSON array")

    model = get_model()
    dim = model.get_sentence_embedding_dimension()

    texts = [build_text(ex) for ex in exercises]
    vectors = model.encode(texts, normalize_embeddings=True).tolist()

    ids = list(range(len(exercises)))
    payloads = []

    for ex, text in zip(exercises, texts):
        payloads.append(
            {
                "kb_id": ex.get("id"),
                "title": ex.get("title"),
                "body_area": ex.get("body_area"),
                "goal": ex.get("goal"),
                "when": ex.get("when"),
                "instructions": ex.get("instructions"),
                "dosage": ex.get("dosage"),
                "cautions": ex.get("cautions"),
                "source": ex.get("source"),
                "text": text,
            }
        )

    with CortexClient(VECTORAI_ADDRESS) as client:
        if not client.has_collection(VECTORAI_COLLECTION):
            client.create_collection(
                name=VECTORAI_COLLECTION,
                dimension=dim,
                distance_metric=DistanceMetric.COSINE,
            )
            print(f"Created collection: {VECTORAI_COLLECTION} (dim={dim})")
        else:
            print(f"Collection already exists: {VECTORAI_COLLECTION}")

        client.batch_upsert(
            VECTORAI_COLLECTION,
            ids=ids,
            vectors=vectors,
            payloads=payloads,
        )

        total = client.count(VECTORAI_COLLECTION)
        print(f"Upserted {len(exercises)} docs. Collection count: {total}")


if __name__ == "__main__":
    main()
