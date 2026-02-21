import { UploadResponse, ScoreResult, ChatResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    body: form
  });

  if (!res.ok) throw new Error(`Upload failed (${res.status})`);
  return res.json();
}

export async function fetchResults(jobId: string): Promise<ScoreResult> {
  const res = await fetch(`${API_URL}/results/${jobId}`);
  if (!res.ok) throw new Error(`Results failed (${res.status})`);
  return res.json();
}

export async function sendChat(message: string, runContext?: Record<string, any>): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, run_context: runContext ?? null })
  });
  if (!res.ok) throw new Error(`Chat failed (${res.status})`);
  return res.json();
}
