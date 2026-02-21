from __future__ import annotations

import json
import sys
from pathlib import Path

# Make apps/api importable when running this script directly
API_ROOT = Path(__file__).resolve().parents[1]   # apps/api
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.cv.analyzer import analyze_running_video
from app.cv.scoring import score_running_form


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_cv_local.py <path_to_video>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"File not found: {video_path}")
        sys.exit(1)

    print(f"Analyzing: {video_path}")
    raw = analyze_running_video(str(video_path))

    print("\n=== RAW OUTPUT ===")
    print(json.dumps(raw, indent=2))

    if not raw.get("ok"):
        print("\nPose detection failed / low confidence. (This is okay for now if video quality is poor.)")
        sys.exit(0)

    scored = score_running_form(raw["raw_metrics"])
    print("\n=== SCORED OUTPUT ===")
    print(json.dumps(scored, indent=2))


if __name__ == "__main__":
    main()