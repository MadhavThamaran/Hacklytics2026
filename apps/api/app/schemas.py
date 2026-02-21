from pydantic import BaseModel
from typing import List, Optional, Literal


class HealthResponse(BaseModel):
    ok: bool


class UploadResponse(BaseModel):
    job_id: str


class MetricScore(BaseModel):
    name: str
    score: int
    value: Optional[float] = None
    unit: Optional[str] = None


class ScoreResult(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "done", "error"]
    overall_score: Optional[int] = None
    metrics: List[MetricScore] = []
    tips: List[str] = []
    overlay_path: Optional[str] = None
    error: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    # later: include run_context and/or body_part extraction
    run_context: Optional[dict] = None


class ChatCitation(BaseModel):
    title: str
    note: str


class ChatResponse(BaseModel):
    message: str
    citations: List[ChatCitation] = []
