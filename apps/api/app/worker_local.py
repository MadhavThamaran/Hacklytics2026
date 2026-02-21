import argparse
import os
import shutil
import time

from .storage import set_job_status, get_job

try:
    from . import databricks_client
except Exception:
    databricks_client = None


def process_video(job_id: str, input_path: str):
    """
    Process video locally. Always stores results locally.
    Updates Databricks SQL metadata if available.
    """
    job = get_job(job_id)
    if not job:
        set_job_status(job_id, "error", {"error": "job not found"})
        return

    try:
        # Simulate processing: copy input to overlay local path
        time.sleep(1)  # simulate work
        
        overlay_name = f"{job_id}-overlay.mp4"
        storage_dir = os.path.join(os.path.dirname(__file__), "..", "storage", "uploads")
        os.makedirs(storage_dir, exist_ok=True)
        overlay_path = os.path.join(storage_dir, overlay_name)
        
        shutil.copyfile(input_path, overlay_path)
        
        # Update local job status
        set_job_status(job_id, "done", {"overlay_path": overlay_path})
        
        # Update Databricks SQL metadata if available
        try:
            if databricks_client is not None:
                databricks_client.execute_sql(
                    f"UPDATE uploads SET status='done', overlay_path='{overlay_path}' WHERE job_id='{job_id}'"
                )
                # Insert minimal results row
                q = (
                    "INSERT INTO video_results (job_id, overall_score, metrics, tips, overlay_path, rubric_version, created_at) "
                    f"VALUES ('{job_id}', 76, map(), array(), '{overlay_path}', '0.1.0', current_timestamp())"
                )
                databricks_client.execute_sql(q)
        except Exception:
            # Databricks update failed but local storage succeeded; continue
            pass
            
    except Exception as e:
        set_job_status(job_id, "error", {"error": str(e)})
        try:
            if databricks_client is not None:
                databricks_client.execute_sql(f"UPDATE uploads SET status='error', error='{str(e)}' WHERE job_id='{job_id}'")
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
