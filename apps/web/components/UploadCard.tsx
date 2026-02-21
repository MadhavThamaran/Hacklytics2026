"use client";

import React from "react";
import { uploadVideo, fetchResults } from "@/lib/api";
import type { ScoreResult } from "@/lib/types";

export default function UploadCard() {
  const [file, setFile] = React.useState<File | null>(null);
  const [jobId, setJobId] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<ScoreResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function onUpload() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const up = await uploadVideo(file);
      setJobId(up.job_id);

      // skeleton: immediate fetch (later: poll while processing)
      const res = await fetchResults(up.job_id);
      setResult(res);
    } catch (e: any) {
      setError(e?.message ?? "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h2 className="h1">Video Form Score</h2>
          <p className="sub">Upload a 10–20s side-view treadmill clip (mock scoring for now).</p>
        </div>
        <span className="badge">MVP Skeleton</span>
      </div>

      <input
        className="input"
        type="file"
        accept="video/*"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />

      <div className="row" style={{ marginTop: 10 }}>
        <button className="btn" disabled={!file || loading} onClick={onUpload}>
          {loading ? "Uploading..." : "Upload & Score"}
        </button>
        {jobId && <span className="small">job_id: {jobId}</span>}
      </div>

      {error && <p className="small" style={{ color: "crimson", marginTop: 10 }}>{error}</p>}

      <hr className="hr" />

      {!result && <p className="small">No results yet. Upload a video to see a stub response.</p>}

      {result && (
        <div>
          <div className="kpi">
            <span>Status</span>
            <span>{result.status}</span>
          </div>
          <div className="kpi">
            <span>Overall score</span>
            <span>{result.overall_score ?? "—"}</span>
          </div>

          <hr className="hr" />

          <div>
            <div className="small" style={{ marginBottom: 6 }}>Metrics</div>
            {result.metrics.map((m) => (
              <div key={m.name} className="kpi">
                <span>{m.name}</span>
                <span>
                  {m.score}
                  {m.value != null ? ` • ${m.value}${m.unit ? ` ${m.unit}` : ""}` : ""}
                </span>
              </div>
            ))}
          </div>

          <hr className="hr" />

          <div>
            <div className="small" style={{ marginBottom: 6 }}>Tips</div>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {result.tips.map((t, i) => (
                <li key={i} className="msg">{t}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
