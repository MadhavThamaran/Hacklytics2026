from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    HealthResponse, UploadResponse, ScoreResult, MetricScore,
    ChatRequest, ChatResponse, ChatCitation
)
from .storage import create_job, save_upload, set_job_status, get_job

app = FastAPI(title="Running Coach API", version="0.1.0")

# Dev-friendly CORS (lock down later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    return {"ok": True}


@app.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    save_path = save_upload(content, file.filename)
    job_id = create_job(filename=save_path)

    # For now: immediately mark as "done" with mock results.
    # Later: queue a CV worker / Databricks job and set to "processing".
    set_job_status(job_id, "done")

    return {"job_id": job_id, "status": "done"}


@app.get("/results/{job_id}", response_model=ScoreResult)
def results(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")

    status = job.get("status", "queued")

    if status == "error":
        return ScoreResult(job_id=job_id, status="error", error=job.get("error", "Unknown error"))

    if status != "done":
        return ScoreResult(job_id=job_id, status=status)

    # Mock scoring payload (replace later with real metrics)
    metrics = [
        MetricScore(name="Cadence", score=78, value=172, unit="spm"),
        MetricScore(name="Overstride", score=66, value=0.18, unit="leg-lengths"),
        MetricScore(name="Torso Lean", score=82, value=7.5, unit="deg"),
        MetricScore(name="Vertical Bounce", score=71, value=5.2, unit="cm"),
    ]
    tips = [
        "Try increasing cadence slightly (+5–10 spm) to reduce impact.",
        "Aim to land closer under your hips to reduce overstriding.",
        "Keep a small forward lean from the ankles (not a waist bend).",
    ]

    return ScoreResult(
        job_id=job_id,
        status="done",
        overall_score=76,
        metrics=metrics,
        tips=tips,
        overlay_url=None,  # later: signed URL or static file path
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Mock response (replace with RAG over Actian VectorAI DB)
    msg = req.message.strip().lower()

    if "shin" in msg:
        response = (
            "For shin discomfort, try: (1) 5–8 min easy walk/jog warm-up, "
            "(2) calf raises 2×12, (3) tibialis raises 2×12, (4) gentle calf stretch 2×30s. "
            "If pain is sharp or persists, consider seeing a professional."
        )
        cites = [
            ChatCitation(title="Mock KB: Tibialis Raises", note="Targets front-of-shin strength; start light."),
            ChatCitation(title="Mock KB: Calf Raises", note="Helps calf/ankle capacity; slow tempo."),
        ]
        return ChatResponse(message=response, citations=cites)

    return ChatResponse(
        message=(
            "Tell me where it hurts (e.g., left knee, right Achilles, shin) and whether you want warm-up, stretching, or strengthening. "
            "I can suggest a short routine (general guidance, not medical advice)."
        ),
        citations=[],
    )
