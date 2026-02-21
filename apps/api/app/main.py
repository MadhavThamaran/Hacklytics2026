from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .rag.coach import run_rag_chat

from .schemas import (
    HealthResponse, UploadResponse, ScoreResult, MetricScore,
    ChatRequest, ChatResponse, ChatCitation
)
from .storage import create_job, save_upload, set_job_status, get_job

import os
import uuid
import subprocess
import tempfile

try:
    from . import databricks_client
except Exception:
    databricks_client = None

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
    
    # Save video locally
    job_id = str(uuid.uuid4())
    save_name = f"{job_id}.mp4"
    save_path = save_upload(content, save_name)
    
    # Create local job entry
    create_job(filename=save_path)
    set_job_status(job_id, "queued", {"filename": save_path})
    
    # Insert into Databricks SQL (metadata only; video stored locally)
    try:
        q = (
            "INSERT INTO uploads (job_id, created_at, video_path, status, overlay_path, rubric_version, error) "
            f"VALUES ('{job_id}', current_timestamp(), '{save_path}', 'queued', NULL, NULL, NULL)"
        )
        databricks_client.execute_sql(q)
    except Exception:
        # If Databricks fails, continue with local storage only
        pass

    # Spawn local worker subprocess (files are always local now)
    worker_py = os.path.join(os.path.dirname(__file__), "worker_local.py")
    input_path = save_path

    try:
        subprocess.Popen(["python", worker_py, "--job_id", job_id, "--input_path", input_path], cwd=os.path.dirname(__file__))
    except Exception:
        # If spawn fails, write status error locally and to Databricks
        set_job_status(job_id, "error", {"error": "worker spawn failed"})
        try:
            databricks_client.execute_sql(f"UPDATE uploads SET status='error', error='worker spawn failed' WHERE job_id='{job_id}'")
        except Exception:
            pass

    return {"job_id": job_id}


@app.get("/results/{job_id}", response_model=ScoreResult)
def results(job_id: str):
    # Try to read metadata from Databricks first; fall back to local jobs.json
    try:
        if databricks_client is not None:
            row = databricks_client.fetch_one(f"SELECT status, overlay_path, error FROM uploads WHERE job_id='{job_id}'")
            if row:
                status, overlay_path, error = row[0], row[1], row[2]
                if status == 'error':
                    return ScoreResult(job_id=job_id, status='error', error=error)
                if status != 'done':
                    return ScoreResult(job_id=job_id, status=status)

                # fetch final results from video_results table
                res = databricks_client.fetch_one(f"SELECT overall_score, metrics, tips FROM video_results WHERE job_id='{job_id}'")
                if not res:
                    return ScoreResult(job_id=job_id, status='processing')
                overall_score, metrics_map, tips_arr = res[0], res[1], res[2]

                metrics_out = []
                try:
                    if metrics_map:
                        for k, v in metrics_map.items():
                            metrics_out.append(MetricScore(name=k, score=int(v.get('score', 0)), value=float(v.get('mean', 0))))
                except Exception:
                    metrics_out = []

                tips = list(tips_arr) if tips_arr else []
                return ScoreResult(job_id=job_id, status='done', overall_score=overall_score, metrics=metrics_out, tips=tips, overlay_path=overlay_path)
    except Exception:
        # Fall through to local storage
        pass

    # Fallback: read from local jobs.json
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    
    status = job.get("status", "queued")
    if status == "error":
        return ScoreResult(job_id=job_id, status="error", error=job.get("error", "Unknown error"))
    if status != "done":
        return ScoreResult(job_id=job_id, status=status)

    # Local mock result (existing behavior)
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

    return ScoreResult(job_id=job_id, status="done", overall_score=76, metrics=metrics, tips=tips, overlay_path=None)


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
