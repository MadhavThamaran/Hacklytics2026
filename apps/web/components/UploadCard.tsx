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

  async function pollResultsUntilDone(id: string) {
    const maxAttempts = 30; // ~30 seconds
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const res = await fetchResults(id);
      setResult(res);

      if (res.status === "done" || res.status === "error") {
        return res;
      }

      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    throw new Error("Analysis timed out. Please try again.");
  }

  async function onUpload() {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setJobId(null);

    try {
      const up = await uploadVideo(file);
      setJobId(up.job_id);

      setResult({
        job_id: up.job_id,
        status: "queued",
        overall_score: null,
        metrics: [],
        tips: [],
        overlay_path: null,
        error: null,
      });

      await pollResultsUntilDone(up.job_id);
    } catch (e: any) {
      setError(e?.message ?? "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  function displayStatus(status?: string | null) {
    if (!status) return "—";
    if (status === "queued" || status === "processing") return "Analyzing";
    if (status === "done") return "Complete";
    if (status === "error") return "Error";
    return status;
  }

  function displayMetricName(name: string) {
    const map: Record<string, string> = {
      Cadence: "Cadence",
      Overstride: "Overstride Ratio",
      "Torso Lean": "Torso Lean",
      "Vertical Bounce": "Vertical Oscillation",
    };
    return map[name] ?? name;
  }

  function formatMetricValue(value: number | null | undefined, unit?: string | null) {
    if (value == null) return "";

    let formatted = "";
    if (Math.abs(value) >= 100) {
      formatted = value.toFixed(0);
    } else if (Math.abs(value) >= 10) {
      formatted = value.toFixed(1);
    } else if (Math.abs(value) >= 1) {
      formatted = value.toFixed(2);
    } else {
      formatted = value.toFixed(4);
    }

    // Optional display-friendly unit tweak
    const prettyUnit = unit === "norm" ? "" : unit ?? "";

    return prettyUnit ? `${formatted} ${prettyUnit}` : formatted;
  }

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h2 className="h1">Video Form Score</h2>
          <p className="sub">Upload a 10–20s side-view treadmill clip for running form analysis.</p>
        </div>
        <span className="badge">CV MVP</span>
      </div>

      <input
        className="input"
        type="file"
        accept="video/*"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />

      <div className="row" style={{ marginTop: 10 }}>
        <button className="btn" disabled={!file || loading} onClick={onUpload}>
          {loading ? "Analyzing..." : "Upload & Score"}
        </button>
        {jobId && <span className="small">job_id: {jobId}</span>}
      </div>

      <p className="small" style={{ marginTop: 8 }}>
        Best results: side view, full body visible, steady camera, good lighting.
      </p>

      {error && (
        <p className="small" style={{ color: "crimson", marginTop: 10 }}>
          {error}
        </p>
      )}

      <hr className="hr" />

      {!result && <p className="small">No results yet. Upload a video to analyze running form.</p>}

      {result && (
        <div>
          <div className="kpi">
            <span>Status</span>
            <span>{displayStatus(result.status)}</span>
          </div>

          <div className="kpi">
            <span>Overall score</span>
            <span>{result.overall_score ?? "—"}</span>
          </div>

          {(result.status === "queued" || result.status === "processing") && (
            <p className="small" style={{ marginTop: 8 }}>
              Processing video... this may take a few seconds.
            </p>
          )}

          {result.status === "error" && (
            <div style={{ marginTop: 8 }}>
              <p className="small" style={{ color: "crimson", margin: 0 }}>
                {result.error ?? "We couldn’t analyze this clip."}
              </p>
              <p className="small" style={{ marginTop: 6 }}>
                Try a side-view clip with your full body visible and less camera shake.
              </p>
            </div>
          )}

          <hr className="hr" />

          <div>
            <div className="small" style={{ marginBottom: 6 }}>Metrics</div>
            {result.metrics.length === 0 ? (
              <p className="small">No metrics yet.</p>
            ) : (
              result.metrics.map((m) => (
                <div key={m.name} className="kpi">
                  <span>{displayMetricName(m.name)}</span>
                  <span>
                    {m.score}
                    {m.value != null ? ` • ${formatMetricValue(m.value, m.unit)}` : ""}
                  </span>
                </div>
              ))
            )}
          </div>

          <hr className="hr" />

          <div>
            <div className="small" style={{ marginBottom: 6 }}>Tips</div>
            {result.tips.length === 0 ? (
              <p className="small">No tips yet.</p>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {result.tips.map((t, i) => (
                  <li key={i} className="msg">{t}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}