from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .rag.coach import run_rag_chat

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
async def chat(req: ChatRequest):
    result = await run_rag_chat(req.message)
    cites = [
        ChatCitation(title=c.get("title", "Source"), note=c.get("note", ""))
        for c in result.get("citations", [])
    ]
    return ChatResponse(
        message=result.get("message", "Sorry, I could not generate a response right now."),
        citations=cites,
    )
