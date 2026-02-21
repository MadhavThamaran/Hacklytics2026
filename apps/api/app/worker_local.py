import argparse
import os
import shutil
import sys

# Make imports work whether this file is run as:
# - module: python -m app.worker_local
# - script: python worker_local.py
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.dirname(THIS_DIR)  # apps/api
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

try:
    from app.storage import set_job_status, get_job
except Exception:
    # Fallback if run as module/package in some contexts
    from .storage import set_job_status, get_job

from app.cv.analyzer import analyze_running_video
from app.cv.scoring import score_running_form

try:
    from app import databricks_client
except Exception:
    try:
        from . import databricks_client
    except Exception:
        databricks_client = None


def _esc_sql(s: str) -> str:
    return str(s).replace("'", "''")


def process_video(job_id: str, input_path: str):
    """
    Process video locally with CV scoring.
    Stores overlay locally (currently just copies original video).
    Updates Databricks SQL metadata/results if available.
    """
    job = get_job(job_id)
    if not job:
        set_job_status(job_id, "error", {"error": "job not found"})
        return

    try:
        # Run CV analysis
        raw = analyze_running_video(input_path)

        if raw.get("ok"):
            scored = score_running_form(raw["raw_metrics"])
            overall_score = int(scored.get("score", 60))
            tips_arr = scored.get("tips", [])
            subscores = scored.get("subscores", {})
            metrics_payload = scored.get("metrics", {})
            warnings_arr = scored.get("warnings", [])
            fallback = False
            error_msg = None
        else:
            # Invalid / non-analyzable clip fallback (no reliable pose / no runner)
            overall_score = 0
            tips_arr = [
                "We could not confidently analyze pose landmarks in this video.",
                "Please make sure the video is of someone running (preferably side-view) with the full body visible.",
            ]
            subscores = {}
            metrics_payload = raw.get("raw_metrics", {})
            warnings_arr = [raw.get("error", "Pose detection failed")]
            fallback = True
            error_msg = raw.get("error")

        # Keep overlay behavior for compatibility (copy original video for now)
        overlay_name = f"{job_id}-overlay.mp4"
        storage_dir = os.path.join(THIS_DIR, "..", "storage", "uploads")
        os.makedirs(storage_dir, exist_ok=True)
        overlay_path = os.path.join(storage_dir, overlay_name)
        shutil.copyfile(input_path, overlay_path)

        # Update local job status
        local_payload = {
            "overlay_path": overlay_path,
            "overall_score": overall_score,
            "tips": tips_arr,
            "metrics": metrics_payload,
            "warnings": warnings_arr,
            "fallback": fallback,
        }
        if error_msg:
            local_payload["error"] = error_msg
        set_job_status(job_id, "done", local_payload)

        # Update Databricks SQL metadata + results row if available
        try:
            if databricks_client is not None:
                databricks_client.execute_sql(
                    f"UPDATE uploads SET status='done', overlay_path='{_esc_sql(overlay_path)}', error=NULL "
                    f"WHERE job_id='{_esc_sql(job_id)}'"
                )

                # Build metrics map in the shape /results expects:
                # map(name -> named_struct('score', <int>, 'mean', <float>))
                metric_entries = []

                # Subscores first (these are likely what the frontend shows)
                for name, score_val in subscores.items():
                    raw_mean = metrics_payload.get(name)
                    if raw_mean is None:
                        raw_mean = score_val
                    try:
                        raw_mean_num = float(raw_mean)
                    except Exception:
                        raw_mean_num = float(score_val)

                    metric_entries.append(
                        f"'{_esc_sql(name)}', named_struct('score', {int(score_val)}, 'mean', {raw_mean_num})"
                    )

                # Add raw metrics (debug/demo visibility)
                raw_metric_keys = [
                    "avg_torso_lean_deg",
                    "overstride_ratio",
                    "knee_drive_ratio",
                    "vertical_oscillation_norm",
                    "cadence_spm_est",
                    "pose_frames",
                    "frames_used",
                ]
                for raw_key in raw_metric_keys:
                    raw_val = metrics_payload.get(raw_key)
                    if raw_val is None:
                        continue
                    try:
                        raw_val_num = float(raw_val)
                    except Exception:
                        continue

                    metric_entries.append(
                        f"'{_esc_sql(raw_key)}', named_struct('score', 0, 'mean', {raw_val_num})"
                    )

                metrics_sql = "map()"
                if metric_entries:
                    metrics_sql = f"map({', '.join(metric_entries)})"

                tips_sql = "array()"
                if tips_arr:
                    tips_sql = "array(" + ", ".join(f"'{_esc_sql(t)}'" for t in tips_arr) + ")"

                # If rerun happens for same job_id, prevent duplicate row issues
                try:
                    databricks_client.execute_sql(
                        f"DELETE FROM video_results WHERE job_id='{_esc_sql(job_id)}'"
                    )
                except Exception:
                    pass

                q = (
                    "INSERT INTO video_results "
                    "(job_id, overall_score, metrics, tips, overlay_path, rubric_version, created_at) "
                    f"VALUES ('{_esc_sql(job_id)}', {overall_score}, {metrics_sql}, {tips_sql}, "
                    f"'{_esc_sql(overlay_path)}', '0.2.0-cv-heuristic', current_timestamp())"
                )
                databricks_client.execute_sql(q)

        except Exception:
            # Databricks update failed but local storage succeeded; continue
            pass

    except Exception as e:
        err = str(e)
        set_job_status(job_id, "error", {"error": err})
        try:
            if databricks_client is not None:
                databricks_client.execute_sql(
                    f"UPDATE uploads SET status='error', error='{_esc_sql(err)}' "
                    f"WHERE job_id='{_esc_sql(job_id)}'"
                )
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job_id", required=True)
    p.add_argument("--input_path", required=True)
    args = p.parse_args()

    process_video(args.job_id, args.input_path)


if __name__ == "__main__":
    main()