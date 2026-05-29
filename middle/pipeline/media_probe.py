"""探测 B-roll 视频时长（供中间层 LLM 规划分镜）。"""
from __future__ import annotations

import subprocess
from pathlib import Path


def probe_video_duration(path: str | Path) -> float | None:
    p = Path(path)
    if not p.is_file():
        return None
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(p),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return max(1.0, float(r.stdout.strip()))
    except Exception:
        return None
