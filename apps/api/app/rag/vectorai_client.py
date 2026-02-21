from typing import Any, Dict, List, Optional
import json
from pathlib import Path

from cortex import CortexClient
from cortex.filters import Filter, Field

from .config import VECTORAI_ADDRESS, VECTORAI_COLLECTION


def _build_filter(body_area: Optional[str], goal: Optional[str]) -> Optional[Filter]:
    f = Filter()
    has_any = False

    if body_area:
        f = f.must(Field("body_area").eq(body_area))
        has_any = True

    if goal:
        f = f.must(Field("goal").eq(goal))
        has_any = True

    return f if has_any else None


def _load_local_payload_map() -> Dict[int, Dict[str, Any]]:
    """
    Map vector ID -> payload using local exercises.json.
    We ingested with ids = [0, 1, 2, ...], so this is stable.
    """
    # apps/api/app/rag/vectorai_client.py -> repo root is parents[4]
    repo_root = Path(__file__).resolve().parents[4]
    data_path = repo_root / "data" / "exercises" / "exercises.json"

    if not data_path.exists():
        return {}

    exercises = json.loads(data_path.read_text(encoding="utf-8"))
    payload_map: Dict[int, Dict[str, Any]] = {}

    for i, ex in enumerate(exercises):
        instructions = ex.get("instructions", [])
        if isinstance(instructions, list):
            instructions_text = " ".join(instructions)
        else:
            instructions_text = str(instructions)

        text = " | ".join(
            [
                str(ex.get("title", "")),
                str(ex.get("body_area", "")),
                str(ex.get("goal", "")),
                str(ex.get("when", "")),
                instructions_text,
                str(ex.get("dosage", "")),
                str(ex.get("cautions", "")),
            ]
        )

        payload_map[i] = {
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

    return payload_map


def search_vectors(
    query_vec: List[float],
    body_area: Optional[str] = None,
    goal: Optional[str] = None,
    top_k: int = 6,
) -> List[Dict[str, Any]]:
    filt = _build_filter(body_area, goal)
    local_payload_map = _load_local_payload_map()

    with CortexClient(VECTORAI_ADDRESS) as client:
        if filt is not None:
            results = client.search_filtered(
                VECTORAI_COLLECTION,
                query=query_vec,
                filter=filt,
                top_k=top_k,
            )
        else:
            results = client.search(
                VECTORAI_COLLECTION,
                query=query_vec,
                top_k=top_k,
            )

    out: List[Dict[str, Any]] = []
    for r in results:
        rid = getattr(r, "id", None)
        payload = getattr(r, "payload", None) or local_payload_map.get(rid, {})
        out.append(
            {
                "id": rid,
                "score": float(getattr(r, "score", 0.0)),
                "payload": payload,
            }
        )
    return out