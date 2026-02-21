"use client";

import React from "react";
import { uploadVideo, fetchResults } from "@/lib/api";
import type { ScoreResult, MetricScore } from "@/lib/types";

import ExpandableCard from './ExpandableCard'

export default function UploadCard() {
  const [file, setFile] = React.useState<File | null>(null);
  const [jobId, setJobId] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<ScoreResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

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
        <h3 className="text-lg font-semibold mb-6">Overall Running Score</h3>

        {/* Score Ring */}
        <div className="flex justify-center mb-8">
          <div className="relative w-32 h-32">
            <div
              className="absolute inset-0 rounded-full ring-fill transition-all"
              style={{
                background: `conic-gradient(from 0deg, rgb(16, 185, 129) 0deg, rgb(16, 185, 129) ${displayScore * 3.6}deg, rgba(255, 255, 255, 0.06) ${displayScore * 3.6}deg)`,
              }}
            />
            <div className={`absolute inset-1 rounded-full bg-zinc-950 flex items-center justify-center ${result ? 'pulse' : ''}`}>
              <div className="text-center">
                <div className="text-3xl font-bold text-emerald-400">{displayScore}</div>
                <div className="text-xs text-zinc-500">/100</div>
              </div>
            </div>
          </div>
        </div>

        {/* Metrics */}
        <div className="space-y-4 mb-6">
          {displayMetrics.map((metric) => {
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
                  <span className="text-sm font-medium">{metric.name}</span>
                  <span className={`text-xs px-2 py-1 rounded-full ${statusColor}`}>
                    {metric.value || metric.score}/100
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
          })}
        </div>

        {/* Opportunity Callout */}
        {result?.tips && result.tips.length > 0 && (
          <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-4">
            <div className="flex items-start gap-3">
              <span className="text-xl">💡</span>
              <div>
                <p className="text-sm font-medium text-amber-100">Your top opportunity:</p>
                <p className="text-sm text-amber-200">{result.tips[0]}</p>
              </div>
            </div>
          </div>
        )}
      </div>

        {jobId && (
          <div className="mt-4 text-xs text-zinc-500">Job ID: {jobId}</div>
        )}
      </div>
    </ExpandableCard>
  );
}
