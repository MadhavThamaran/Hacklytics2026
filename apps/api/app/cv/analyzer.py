from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import math
import cv2
import numpy as np
import mediapipe as mp


@dataclass
class RawMetrics:
    frames_total: int
    frames_used: int
    pose_frames: int
    avg_torso_lean_deg: Optional[float]
    overstride_ratio: Optional[float]
    knee_drive_ratio: Optional[float]
    vertical_oscillation_norm: Optional[float]
    cadence_spm_est: Optional[float]


def _angle_from_vertical(p1, p2) -> float:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return math.degrees(math.atan2(dx, -dy))


def analyze_running_video(video_path: str, sample_every_n: int = 2) -> Dict[str, Any]:
    mp_pose = mp.solutions.pose

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_idx = 0
    frames_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    torso_leans = []
    hip_y_series = []
    left_ankle_y = []
    right_ankle_y = []
    overstride_events = []
    knee_drive_vals = []

    pose_frames = 0
    frames_used = 0

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

            frame_idx += 1
            if frame_idx % sample_every_n != 0:
                continue

            frames_used += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)
            if not res.pose_landmarks:
                continue

            pose_frames += 1
            lm = res.pose_landmarks.landmark

            def pt(i):
                return (lm[i].x, lm[i].y, lm[i].visibility)

            L_SHOULDER, R_SHOULDER = 11, 12
            L_HIP, R_HIP = 23, 24
            L_KNEE, R_KNEE = 25, 26
            L_ANKLE, R_ANKLE = 27, 28

            left_vis = min(pt(L_SHOULDER)[2], pt(L_HIP)[2], pt(L_ANKLE)[2], pt(L_KNEE)[2])
            right_vis = min(pt(R_SHOULDER)[2], pt(R_HIP)[2], pt(R_ANKLE)[2], pt(R_KNEE)[2])
            use_left = left_vis >= right_vis

            if use_left:
                sh = pt(L_SHOULDER)
                hip = pt(L_HIP)
                knee = pt(L_KNEE)
                ankle = pt(L_ANKLE)
            else:
                sh = pt(R_SHOULDER)
                hip = pt(R_HIP)
                knee = pt(R_KNEE)
                ankle = pt(R_ANKLE)

            torso_leans.append(abs(_angle_from_vertical((sh[0], sh[1]), (hip[0], hip[1]))))

            hip_center_y = (pt(L_HIP)[1] + pt(R_HIP)[1]) / 2.0
            hip_y_series.append(hip_center_y)

            left_ankle_y.append(pt(L_ANKLE)[1])
            right_ankle_y.append(pt(R_ANKLE)[1])

            shoulder_center = (
                (pt(L_SHOULDER)[0] + pt(R_SHOULDER)[0]) / 2.0,
                (pt(L_SHOULDER)[1] + pt(R_SHOULDER)[1]) / 2.0,
            )
            hip_center = (
                (pt(L_HIP)[0] + pt(R_HIP)[0]) / 2.0,
                (pt(L_HIP)[1] + pt(R_HIP)[1]) / 2.0,
            )
            body_scale = max(0.05, math.dist(shoulder_center, hip_center))

            ankle_ahead = abs(ankle[0] - hip[0]) / body_scale
            overstride_events.append(ankle_ahead)

            knee_drive = abs(hip[1] - knee[1]) / body_scale
            knee_drive_vals.append(knee_drive)

    cap.release()

    if pose_frames < 10:
        return {
            "ok": False,
            "error": "Pose detection confidence too low or too few valid frames",
            "raw_metrics": RawMetrics(
                frames_total=frames_total,
                frames_used=frames_used,
                pose_frames=pose_frames,
                avg_torso_lean_deg=None,
                overstride_ratio=None,
                knee_drive_ratio=None,
                vertical_oscillation_norm=None,
                cadence_spm_est=None,
            ).__dict__,
        }

    avg_torso_lean_deg = float(np.median(torso_leans)) if torso_leans else None
    overstride_ratio = float(np.median(overstride_events)) if overstride_events else None
    knee_drive_ratio = float(np.median(knee_drive_vals)) if knee_drive_vals else None
    vertical_oscillation_norm = float(np.std(hip_y_series)) if len(hip_y_series) > 5 else None

    cadence_spm_est = None
    try:
        series = np.array(left_ankle_y if len(left_ankle_y) >= len(right_ankle_y) else right_ankle_y, dtype=float)
        if len(series) > 20:
            series = series - np.mean(series)
            peaks = 0
            for i in range(1, len(series) - 1):
                if series[i] > series[i - 1] and series[i] > series[i + 1]:
                    peaks += 1
            duration_sec = max(1e-6, (frames_used * sample_every_n) / fps)
            cadence_spm_est = float((peaks / duration_sec) * 60.0)
            cadence_spm_est = float(np.clip(cadence_spm_est, 120, 220))
    except Exception:
        cadence_spm_est = None

    return {
        "ok": True,
        "raw_metrics": RawMetrics(
            frames_total=frames_total,
            frames_used=frames_used,
            pose_frames=pose_frames,
            avg_torso_lean_deg=avg_torso_lean_deg,
            overstride_ratio=overstride_ratio,
            knee_drive_ratio=knee_drive_ratio,
            vertical_oscillation_norm=vertical_oscillation_norm,
            cadence_spm_est=cadence_spm_est,
        ).__dict__,
    }