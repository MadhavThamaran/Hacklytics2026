import asyncio
from typing import Any, Dict, List, Optional, Tuple

from .config import RAG_TOP_K
from .embedder import embed_text
from .vectorai_client import search_vectors


BODY_PARTS = {
    "shin": ["shin", "shin splint", "tibialis"],
    "knee": ["knee", "runner's knee", "patellar"],
    "achilles": ["achilles", "heel"],
    "hip": ["hip", "glute", "it band", "outer hip"],
    "foot": ["foot", "arch", "plantar"],
    "ankle": ["ankle"],
    "calf": ["calf"],
    "hamstring": ["hamstring", "back of thigh"],
    "quad": ["quad", "quads", "front of thigh"],
    "low_back": ["low back", "lower back", "back pain", "lumbar"],
}

INTENTS = {
    "warmup": ["warmup", "warm-up", "pre-run", "before run"],
    "stretch": ["stretch", "stretching", "post-run", "after run"],
    "mobility": ["mobility"],
    "strength": ["strength", "strengthen"],
}


def extract_signals(message: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    m = message.lower()

    side = None
    if "left" in m:
        side = "left"
    elif "right" in m:
        side = "right"
    elif "both" in m:
        side = "both"

    body_area = None
    for key, kws in BODY_PARTS.items():
        if any(kw in m for kw in kws):
            body_area = key
            break

    intent = None
    for key, kws in INTENTS.items():
        if any(kw in m for kw in kws):
            intent = key
            break

    return body_area, side, intent


def _pick_first(docs: List[Dict[str, Any]], goal: str) -> Optional[Dict[str, Any]]:
    for d in docs:
        if d.get("payload", {}).get("goal") == goal:
            return d
    return None


def _fmt_item(doc: Optional[Dict[str, Any]], label: str, fallback: str) -> str:
    if not doc:
        return f"- {label}: {fallback}"
    p = doc.get("payload", {})
    title = p.get("title", "Exercise")
    dosage = p.get("dosage", "Use comfortable dosage")
    return f"- {label}: {title} ({dosage})"


def build_general_fallback_response() -> str:
    lines = [
        "Plan:",
        "- Warm-up (2-5 min): Easy walk/jog, leg swings, and ankle circles.",
        "- Mobility / Stretch (2-5 min): Gentle calf/ankle mobility and light hip mobility.",
        "- Strength (8-12 min): Glute bridges and calf raises with controlled tempo.",
        "",
        "Dosage:",
        "- Start easy and keep pain low. Increase gradually only if symptoms stay mild during and after the run.",
        "",
        "Form tips (1-2):",
        "- Avoid limping or forcing range of motion.",
        "- Reduce pace/volume if pain increases while running.",
        "",
        "Safety:",
        "- This is general exercise guidance, not a diagnosis. If pain is severe, sharp, worsening, or persistent, see a clinician.",
        "",
        "To tailor this better, tell me where it hurts (shin, knee, Achilles, hip, foot, ankle, calf) and whether you want warm-up, stretching, or strengthening.",
    ]
    return "\n".join(lines)


def build_response(docs: List[Dict[str, Any]], body_area: Optional[str]) -> str:
    if body_area is None:
        return build_general_fallback_response()

    warm = _pick_first(docs, "warmup")
    mob = _pick_first(docs, "mobility") or _pick_first(docs, "stretch")
    strength = _pick_first(docs, "strength")

    lines = [
        "Plan:",
        _fmt_item(warm, "Warm-up (2-5 min)", "easy walk/jog + controlled leg swings"),
        _fmt_item(mob, "Mobility / Stretch (2-5 min)", "gentle ankle/calf mobility, no forced range"),
        _fmt_item(strength, "Strength (8-12 min)", "controlled lower-leg/hip strength work"),
        "",
        "Dosage:",
        "- Start easy and increase only if symptoms stay mild during and after the run.",
        "",
        "Form tips (1-2):",
        "- Keep movements controlled and pain low; do not force range of motion.",
        "- If running form changes a lot (limping), stop and scale back.",
        "",
        "Safety:",
        "- This is general exercise guidance, not a diagnosis. If pain is severe, sharp, worsening, or persistent, see a clinician.",
    ]
    return "\n".join(lines)


async def run_rag_chat(message: str) -> Dict[str, Any]:
    body_area, side, intent = extract_signals(message)

    goal_filter = intent if intent in {"warmup", "stretch", "mobility", "strength"} else None

    query_vec = await asyncio.to_thread(embed_text, message)

    # If no body area recognized, search broadly (no body filter)
    if body_area is None:
        docs = await asyncio.to_thread(
            search_vectors,
            query_vec,
            None,
            goal_filter,
            RAG_TOP_K,
        )
    else:
        docs = await asyncio.to_thread(
            search_vectors,
            query_vec,
            body_area,
            goal_filter,
            RAG_TOP_K,
        )

        # Retry without intent filter if too restrictive
        if not docs and goal_filter is not None:
            docs = await asyncio.to_thread(
                search_vectors,
                query_vec,
                body_area,
                None,
                RAG_TOP_K,
            )

    response_text = build_response(docs, body_area)

    citations = []
    for d in docs[:5]:
        p = d.get("payload", {})
        title = p.get("title")
        source = p.get("source", "Coach-curated running exercise KB")
        if title:
            citations.append({"title": title, "note": source})

    return {
        "message": response_text,
        "citations": citations,
    }