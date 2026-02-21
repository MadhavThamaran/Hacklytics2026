import argparse
import os
import shutil
import subprocess
import sys
import tempfile

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


def _ffmpeg_exe() -> str | None:
    """
    Return ffmpeg executable path if available, else None.
    Works with PATH or common winget install locations.
    """
    # PATH first
    ff = shutil.which("ffmpeg")
    if ff:
        return ff

    # Common Windows fallback guesses (winget usually adds PATH, but just in case)
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
        os.path.expandvars(r"%ProgramFiles%\ffmpeg\bin\ffmpeg.exe"),
        os.path.expandvars(r"%ProgramFiles%\Gyan\FFmpeg\bin\ffmpeg.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def _reencode_browser_safe_mp4(src_path: str, dst_path: str) -> None:
    """
    Re-encode video to browser-safe MP4 (H.264 + yuv420p + faststart) using ffmpeg.
    Raises on failure.
    """
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-i", src_path,
        "-an",                     # drop audio for demo reliability (optional)
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        dst_path,
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg re-encode failed: {proc.stderr[-1000:]}")


def _generate_pose_overlay_video(input_path: str, output_path: str, max_frames: int | None = None) -> None:
    """
    Generate an annotated overlay video with MediaPipe Pose landmarks.
    Writes a browser-safe MP4 to output_path.
    Strategy:
      1) Render annotated video with OpenCV to a temp mp4
      2) Re-encode with ffmpeg to H.264/yuv420p for browser playback
    Raises exception on failure (caller can fallback to copy).
    """
    import cv2
    import mediapipe as mp

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError("Could not open input video for overlay generation")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if width <= 0 or height <= 0:
        cap.release()
        raise RuntimeError("Invalid video dimensions")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write to a temp mp4 first (OpenCV codec), then ffmpeg -> browser-safe mp4
    temp_dir = tempfile.mkdtemp(prefix="pose_overlay_")
    temp_raw_mp4 = os.path.join(temp_dir, "overlay_raw.mp4")

    writer = None
    writer_errs = []
    for fourcc_name in ["mp4v", "avc1"]:
        fourcc = cv2.VideoWriter_fourcc(*fourcc_name)
        w = cv2.VideoWriter(temp_raw_mp4, fourcc, fps, (width, height))
        if w.isOpened():
            writer = w
            break
        writer_errs.append(fourcc_name)

    if writer is None:
        cap.release()
        raise RuntimeError(f"Could not open VideoWriter (tried codecs: {writer_errs})")

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    frame_count = 0
    pose_detected_frames = 0

    try:
        with mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as pose:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                frame_count += 1
                if max_frames is not None and frame_count > max_frames:
                    break

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)

                annotated = frame.copy()

                if result.pose_landmarks:
                    pose_detected_frames += 1
                    mp_drawing.draw_landmarks(
                        annotated,
                        result.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style(),
                    )

                cv2.putText(
                    annotated,
                    "Running Coach Pose Overlay",
                    (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

                writer.write(annotated)
    finally:
        cap.release()
        writer.release()

    # Re-encode for browser compatibility
    _reencode_browser_safe_mp4(temp_raw_mp4, output_path)

    # Best-effort temp cleanup
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    # We intentionally do not raise if no pose frames detected; overlay is still useful for demo.


def process_video(job_id: str, input_path: str):
    """
    Process video locally with CV scoring.
    Stores overlay locally (annotated pose video if possible; otherwise copies original).
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

        # Create overlay path
        overlay_name = f"{job_id}-overlay.mp4"
        storage_dir = os.path.join(THIS_DIR, "..", "storage", "uploads")
        os.makedirs(storage_dir, exist_ok=True)
        overlay_path = os.path.join(storage_dir, overlay_name)

        # Try generating annotated overlay; fallback to browser-safe re-encode of original; final fallback copy
        overlay_generated = False
        overlay_error = None
        ffmpeg_used = False

        try:
            _generate_pose_overlay_video(input_path, overlay_path)
            overlay_generated = True
            ffmpeg_used = True
        except Exception as e:
            overlay_error = str(e)

            # Try at least making the original browser-safe if ffmpeg exists
            try:
                _reencode_browser_safe_mp4(input_path, overlay_path)
                ffmpeg_used = True
            except Exception as e2:
                # Final fallback: raw copy (may not play in browser depending on codec)
                overlay_error = f"{overlay_error} | fallback re-encode failed: {e2}"
                shutil.copyfile(input_path, overlay_path)

        # Update local job status
        local_payload = {
            "overlay_path": overlay_path,
            "overall_score": overall_score,
            "tips": tips_arr,
            "metrics": metrics_payload,
            "warnings": warnings_arr,
            "fallback": fallback,
            "overlay_generated": overlay_generated,
            "ffmpeg_used": ffmpeg_used,
        }
        if overlay_error:
            local_payload["overlay_error"] = overlay_error
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
                    f"'{_esc_sql(overlay_path)}', '0.2.1-cv-overlay-ffmpeg', current_timestamp())"
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