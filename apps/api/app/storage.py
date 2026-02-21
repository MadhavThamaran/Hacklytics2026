import os
import json
import uuid
from typing import Dict, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
JOBS_PATH = os.path.join(STORAGE_DIR, "jobs.json")

os.makedirs(UPLOADS_DIR, exist_ok=True)


def _load_jobs() -> Dict[str, Any]:
    if not os.path.exists(JOBS_PATH):
        return {}
    try:
        with open(JOBS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_jobs(jobs: Dict[str, Any]) -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)


def create_job(filename: str) -> str:
    jobs = _load_jobs()
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "filename": filename,
    }
    _save_jobs(jobs)
    return job_id


def set_job_status(job_id: str, status: str, extra: Dict[str, Any] | None = None) -> None:
    jobs = _load_jobs()
    if job_id not in jobs:
        return
    jobs[job_id]["status"] = status
    if extra:
        jobs[job_id].update(extra)
    _save_jobs(jobs)


def get_job(job_id: str) -> Dict[str, Any] | None:
    jobs = _load_jobs()
    return jobs.get(job_id)


def save_upload(file_bytes: bytes, original_name: str) -> str:
    safe_name = original_name.replace("/", "_").replace("\\", "_")
    path = os.path.join(UPLOADS_DIR, safe_name)
    # if name exists, make it unique
    if os.path.exists(path):
        root, ext = os.path.splitext(safe_name)
        path = os.path.join(UPLOADS_DIR, f"{root}-{uuid.uuid4().hex[:8]}{ext}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path
