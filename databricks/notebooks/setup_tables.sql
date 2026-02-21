-- Create uploads table
CREATE TABLE IF NOT EXISTS uploads (
  job_id STRING,
  created_at TIMESTAMP,
  video_path STRING,
  status STRING,
  overlay_path STRING,
  rubric_version STRING,
  error STRING
) USING DELTA;

-- Create video_results table
CREATE TABLE IF NOT EXISTS video_results (
  job_id STRING,
  overall_score INT,
  metrics MAP<STRING, STRUCT<mean:DOUBLE, score:INT>>, 
  tips ARRAY<STRING>,
  overlay_path STRING,
  rubric_version STRING,
  created_at TIMESTAMP
) USING DELTA;
