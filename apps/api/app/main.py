from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    from .rag.coach import run_rag_chat
except Exception:
    run_rag_chat = None

from .schemas import (
    HealthResponse, UploadResponse, ScoreResult, MetricScore,
    ChatRequest, ChatResponse, ChatCitation
)
from .storage import create_job, save_upload, set_job_status, get_job

import sys
import os
import subprocess

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

# Serve local storage files (videos / overlays) at /static/*
# Maps apps/api/storage/... -> /static/...
_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")
app.mount("/static", StaticFiles(directory=_STORAGE_DIR), name="static")


def _to_static_url(path: str | None) -> str | None:
    """Convert local filesystem storage path to browser-friendly /static URL."""
    if not path:
        return None

    norm = str(path).replace("\\", "/")
    marker = "/storage/"
    idx = norm.lower().find(marker)
    if idx == -1:
        return path  # fallback if path is already URL-like or unexpected

    rel = norm[idx + len(marker):]
    return f"/static/{rel}"


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

    # Create local job entry first (this is the source of truth for job_id)
    job_id = create_job(filename="pending")

    # Save video locally using the same job_id
    save_name = f"{job_id}.mp4"
    save_path = save_upload(content, save_name)

    # Update local job with real filename/path
    set_job_status(job_id, "queued", {"filename": save_path})

    # Insert into Databricks SQL (metadata only; video stored locally)
    try:
        if databricks_client is not None:
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

    # Prefer dedicated CV worker venv to avoid protobuf conflicts with chat/cortex
    cv_python = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".venv_cv", "Scripts", "python.exe")
    )
    python_cmd = cv_python if os.path.exists(cv_python) else sys.executable

    try:
        subprocess.Popen(
            [python_cmd, worker_py, "--job_id", job_id, "--input_path", input_path],
            cwd=os.path.dirname(__file__),
        )
    except Exception:
        # If spawn fails, write status error locally and to Databricks
        set_job_status(job_id, "error", {"error": "worker spawn failed"})
        try:
            if databricks_client is not None:
                databricks_client.execute_sql(
                    f"UPDATE uploads SET status='error', error='worker spawn failed' WHERE job_id='{job_id}'"
                )
        except Exception:
            pass

    return {"job_id": job_id}


@app.get("/results/{job_id}", response_model=ScoreResult)
def results(job_id: str):
    # 1) Prefer local jobs.json first (best for CV demo reliability)
    job = get_job(job_id)
    if job:
        status = job.get("status", "queued")

        if status == "error":
            return ScoreResult(
                job_id=job_id,
                status="error",
                error=job.get("error", "Unknown error"),
            )

        if status != "done":
            return ScoreResult(job_id=job_id, status=status)

        # Local done state: build response from CV payload (top-level fields in jobs.json)
        overall_score = job.get("overall_score")
        tips = job.get("tips", []) or []
        overlay_path = job.get("overlay_path")
        overlay_url = _to_static_url(overlay_path)
        metrics_payload = job.get("metrics", {}) or {}

        display_metric_map = [
            ("cadence_spm_est", "Cadence", "spm"),
            ("overstride_ratio", "Overstride", "leg-lengths"),
            ("avg_torso_lean_deg", "Torso Lean", "deg"),
            ("vertical_oscillation_norm", "Vertical Bounce", "norm"),
        ]

        metrics = []
        for raw_key, display_name, unit in display_metric_map:
            raw_val = metrics_payload.get(raw_key)
            if raw_val is None:
                continue
            try:
                value = float(raw_val)
            except Exception:
                continue

            # Demo-friendly score guesses when local payload only has raw values
            score_guess = 75
            if raw_key == "cadence_spm_est":
                score_guess = 85 if 160 <= value <= 185 else 60
            elif raw_key == "avg_torso_lean_deg":
                score_guess = 85 if 5 <= value <= 15 else 65
            elif raw_key == "overstride_ratio":
                score_guess = 85 if value <= 1.2 else 60
            elif raw_key == "vertical_oscillation_norm":
                score_guess = 85 if value <= 0.02 else 65

            metrics.append(
                MetricScore(
                    name=display_name,
                    score=int(score_guess),
                    value=value,
                    unit=unit,
                )
            )

        return ScoreResult(
            job_id=job_id,
            status="done",
            overall_score=int(overall_score) if overall_score is not None else None,
            metrics=metrics,
            tips=tips,
            overlay_path=overlay_url,
        )

    # 2) If not in local storage, try Databricks (fallback)
    try:
        if databricks_client is not None:
            row = databricks_client.fetch_one(
                f"SELECT status, overlay_path, error FROM uploads WHERE job_id='{job_id}'"
            )
            if row:
                status, overlay_path, error = row[0], row[1], row[2]
                if status == "error":
                    return ScoreResult(job_id=job_id, status="error", error=error)
                if status != "done":
                    return ScoreResult(job_id=job_id, status=status)

                res = databricks_client.fetch_one(
                    f"SELECT overall_score, metrics, tips FROM video_results WHERE job_id='{job_id}'"
                )
                if not res:
                    return ScoreResult(job_id=job_id, status="processing")

                overall_score, metrics_map, tips_arr = res[0], res[1], res[2]

                metrics_out = []
                try:
                    if metrics_map:
                        for k, v in metrics_map.items():
                            metrics_out.append(
                                MetricScore(
                                    name=k,
                                    score=int(v.get("score", 0)),
                                    value=float(v.get("mean", 0)),
                                )
                            )
                except Exception:
                    metrics_out = []

                tips = list(tips_arr) if tips_arr else []
                overlay_url = _to_static_url(overlay_path)
                return ScoreResult(
                    job_id=job_id,
                    status="done",
                    overall_score=overall_score,
                    metrics=metrics_out,
                    tips=tips,
                    overlay_path=overlay_url,
                )
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="job_id not found")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if run_rag_chat is None:
        raise HTTPException(status_code=503, detail="Chat feature temporarily unavailable in this environment")
    result = await run_rag_chat(req.message)
    cites = [
        ChatCitation(title=c.get("title", "Source"), note=c.get("note", ""))
        for c in result.get("citations", [])
    ]
    return ChatResponse(
        message=result.get("message", "Sorry, I could not generate a response right now."),
        citations=cites,
    )