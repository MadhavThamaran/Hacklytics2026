"use client";

import React from "react";
import { uploadVideo, fetchResults } from "@/lib/api";
import type { ScoreResult, MetricScore } from "@/lib/types";

import ExpandableCard from './ExpandableCard'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function UploadCard() {
  const [file, setFile] = React.useState<File | null>(null);
  const [jobId, setJobId] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<ScoreResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  async function pollResultsUntilDone(id: string) {
    const maxAttempts = 180; // ~60 seconds
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

  // Backend utility functions for display formatting
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

    const prettyUnit = unit === "norm" ? "" : unit ?? "";
    return prettyUnit ? `${formatted} ${prettyUnit}` : formatted;
  }

  function overlayUrl(path?: string | null) {
    if (!path) return null;
    if (path.startsWith("http://") || path.startsWith("https://")) return path;
    return `${API_URL}${path}`;
  }

  const videoUrl = overlayUrl(result?.overlay_path);

  const handleDropZoneClick = () => {
    fileInputRef.current?.click();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      setFile(files[0]);
    }
  };

  // Mock data for display when no real results
  const mockOverallScore = 82;
  const mockMetrics: MetricScore[] = [
    { name: "Stride Length", score: 30, status: "Needs Work", color: "bg-amber-400" },
    { name: "Posture", score: 70, status: "Good", color: "bg-emerald-400" },
    { name: "Cadence", score: 95, status: "Excellent", color: "bg-emerald-300" },
    { name: "Stability", score: 45, status: "Fair", color: "bg-orange-400" },
  ];

  const displayScore = result?.overall_score ?? mockOverallScore;
  const displayMetrics = (result?.metrics && result.metrics.length > 0)
    ? result.metrics
    : mockMetrics;

  return (
    <ExpandableCard className="">
      <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur shadow-xl p-6">
      {/* Card Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">🏃</span>
          <h2 className="text-xl font-semibold">Video Form Score</h2>
        </div>
        <div className="h-1 w-32 bg-gradient-to-r from-emerald-400/60 to-amber-400/60 rounded-full" />
      </div>

      {/* Dropzone */}
      <div
        onClick={handleDropZoneClick}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className="rounded-xl border border-dashed border-white/10 bg-black/20 hover:border-white/20 p-6 cursor-pointer transition mb-4"
      >
        <input
          ref={fileInputRef}
          className="sr-only"
          type="file"
          accept="video/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <div className="text-center">
          <div className="text-3xl mb-2">📹</div>
          <p className="text-zinc-200 font-medium">Drag & drop a side-view running clip</p>
          <p className="text-zinc-500 text-sm">MP4, MOV • 10–20s</p>
          {file && <p className="text-emerald-400 text-sm mt-2">✓ {file.name}</p>}
        </div>
      </div>

      {/* Analyze Button */}
      <button
        className="w-full rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-medium px-5 py-2.5 disabled:opacity-50 transition mb-6"
        disabled={!file || loading}
        onClick={onUpload}
      >
        {loading ? "Analyzing Run..." : "Analyze Run"}
      </button>

      {/* Error Display */}
      {error && (
        <div className="rounded-xl bg-red-500/10 border border-red-400/20 text-red-100 p-3 mb-6 text-sm">
          {error}
        </div>
      )}

      {/* Results Section */}
      <div>
        {result && (
          <div>
            {/* Status Display */}
            <div className="mb-6 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-zinc-400">Status</span>
                <span className="text-sm font-medium">{displayStatus(result.status)}</span>
              </div>
              {jobId && (
                <div className="text-xs text-zinc-500">Job ID: {jobId}</div>
              )}
            </div>

            {/* Processing State */}
            {(result.status === "queued" || result.status === "processing") && (
              <p className="text-sm text-zinc-400 mb-6">
                Processing video... this may take a few seconds.
              </p>
            )}

            {/* Error State */}
            {result.status === "error" && (
              <div className="mb-6 space-y-2">
                <p className="text-sm text-red-300">
                  {result.error ?? "We couldn't analyze this clip."}
                </p>
                <p className="text-sm text-zinc-400">
                  Try a side-view clip with your full body visible and less camera shake.
                </p>
              </div>
            )}

            {result.status === "done" && (
              <>
                <hr className="border-white/10 my-6" />

                <h3 className="text-lg font-semibold mb-6">Overall Running Score</h3>

                {/* Score Ring */}
                <div className="flex justify-center mb-8">
                  <div className="relative w-32 h-32">
                    <div
                      className="absolute inset-0 rounded-full ring-fill transition-all"
                      style={{
                        background: `conic-gradient(from 0deg, rgb(16, 185, 129) 0deg, rgb(16, 185, 129) ${(result.overall_score ?? 0) * 3.6}deg, rgba(255, 255, 255, 0.06) ${(result.overall_score ?? 0) * 3.6}deg)`,
                      }}
                    />
                    <div className="absolute inset-1 rounded-full bg-zinc-950 flex items-center justify-center">
                      <div className="text-center">
                        <div className="text-3xl font-bold text-emerald-400">{result.overall_score ?? "—"}</div>
                        <div className="text-xs text-zinc-500">/100</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Metrics */}
                <div className="space-y-4 mb-6">
                  {result.metrics.length === 0 ? (
                    <p className="text-sm text-zinc-400">No metrics yet.</p>
                  ) : (
                    result.metrics.map((metric) => {
                      const scorePercent = Math.min(100, metric.score ?? 0);
                      const statusColor =
                        scorePercent >= 80
                          ? "bg-emerald-500/20 text-emerald-300"
                          : scorePercent >= 50
                          ? "bg-amber-500/20 text-amber-300"
                          : "bg-orange-500/20 text-orange-300";

                      return (
                        <div key={metric.name}>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">{displayMetricName(metric.name)}</span>
                            <span className={`text-xs px-2 py-1 rounded-full ${statusColor}`}>
                              {metric.score}
                              {metric.value != null ? ` • ${formatMetricValue(metric.value, metric.unit)}` : ""}
                            </span>
                          </div>
                          <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${metric.color || "bg-emerald-400"} transition-all bar-fill`}
                              style={{ width: `${scorePercent}%` }}
                            />
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Tips */}
                {result.tips && result.tips.length > 0 && (
                  <>
                    <hr className="border-white/10 my-6" />
                    <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-4">
                      <div className="flex items-start gap-3">
                        <span className="text-xl">💡</span>
                        <div>
                          <p className="text-sm font-medium text-amber-100">Your top opportunity:</p>
                          <p className="text-sm text-amber-200">{result.tips[0]}</p>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {/* Video Overlay */}
                {videoUrl && (
                  <>
                    <hr className="border-white/10 my-6" />
                    <div>
                      <div className="text-sm text-zinc-400 mb-3">Pose Overlay Video (debug/demo)</div>
                      <video
                        key={videoUrl}
                        controls
                        preload="metadata"
                        style={{ width: "100%", borderRadius: 12, background: "#000" }}
                        src={videoUrl}
                      />
                      <p className="text-sm text-zinc-500 mt-3">
                        Overlay currently mirrors the uploaded clip. Next step: draw pose landmarks on frames.
                      </p>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}

        {!result && (
          <div className="text-center py-8">
            <p className="text-sm text-zinc-400">No results yet. Upload a video to analyze running form.</p>
            <p className="text-xs text-zinc-500 mt-2">Best results: side view, full body visible, steady camera, good lighting.</p>
          </div>
        )}
      </div>
      </div>
    </ExpandableCard>
  );
}
