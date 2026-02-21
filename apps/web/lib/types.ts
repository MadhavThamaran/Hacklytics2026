export type UploadResponse = {
  job_id: string;
  status: "queued" | "processing" | "done" | "error";
};

export type MetricScore = {
  name: string;
  score: number;
  value?: number | null;
  unit?: string | null;
};

export type ScoreResult = {
  job_id: string;
  status: "queued" | "processing" | "done" | "error";
  overall_score?: number | null;
  metrics: MetricScore[];
  tips: string[];
  overlay_url?: string | null;
  error?: string | null;
};

export type ChatResponse = {
  message: string;
  citations: { title: string; note: string }[];
};
