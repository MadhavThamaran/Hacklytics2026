from __future__ import annotations
from typing import Any, Dict, List


def _score_range(value, ideal_low, ideal_high, bad_low, bad_high) -> int:
    if value is None:
        return 60

    if ideal_low <= value <= ideal_high:
        return 100

    if value < ideal_low:
        if value <= bad_low:
            return 40
        frac = (value - bad_low) / max(1e-6, (ideal_low - bad_low))
        return int(40 + 60 * frac)

    if value > ideal_high:
        if value >= bad_high:
            return 40
        frac = (bad_high - value) / max(1e-6, (bad_high - ideal_high))
        return int(40 + 60 * frac)

    return 60


def score_running_form(raw: Dict[str, Any]) -> Dict[str, Any]:
    posture = _score_range(
        raw.get("avg_torso_lean_deg"), ideal_low=5, ideal_high=15, bad_low=0, bad_high=25
    )

    overstride = raw.get("overstride_ratio")
    if overstride is None:
        stride = 60
    elif overstride <= 1.2:
        stride = 100
    elif overstride >= 2.2:
        stride = 45
    else:
        stride = int(100 - ((overstride - 1.2) / (2.2 - 1.2)) * 55)

    vo = raw.get("vertical_oscillation_norm")
    if vo is None:
        stability = 60
    elif vo <= 0.015:
        stability = 100
    elif vo >= 0.05:
        stability = 45
    else:
        stability = int(100 - ((vo - 0.015) / (0.05 - 0.015)) * 55)

    cadence = raw.get("cadence_spm_est")
    if cadence is None:
        cadence_proxy = 60
    elif 160 <= cadence <= 185:
        cadence_proxy = 100
    elif cadence < 145 or cadence > 205:
        cadence_proxy = 50
    else:
        cadence_proxy = 80

    final_score = int(round(
        0.30 * posture +
        0.35 * stride +
        0.20 * stability +
        0.15 * cadence_proxy
    ))

    tips: List[str] = []
    warnings: List[str] = ["Best results come from side-view videos with full body visible."]

    if posture < 75:
        tips.append("Maintain a slight forward lean from the ankles, not by bending at the waist.")
    if stride < 75:
        tips.append("Try landing with your foot closer under your hips to reduce overstriding.")
    if stability < 75:
        tips.append("Focus on smooth forward motion and reduce excess vertical bounce.")
    if cadence_proxy < 75:
        tips.append("Try slightly quicker, lighter steps to improve cadence and reduce braking forces.")
    if not tips:
        tips.append("Form looks solid overall. Maintain consistency and gradually build volume.")

    return {
        "score": final_score,
        "subscores": {
            "posture": posture,
            "stride": stride,
            "stability": stability,
            "cadence_proxy": cadence_proxy,
        },
        "tips": tips[:3],
        "warnings": warnings,
        "metrics": {
            "avg_torso_lean_deg": raw.get("avg_torso_lean_deg"),
            "overstride_ratio": raw.get("overstride_ratio"),
            "knee_drive_ratio": raw.get("knee_drive_ratio"),
            "vertical_oscillation_norm": raw.get("vertical_oscillation_norm"),
            "cadence_spm_est": raw.get("cadence_spm_est"),
            "pose_frames": raw.get("pose_frames"),
            "frames_used": raw.get("frames_used"),
        },
    }