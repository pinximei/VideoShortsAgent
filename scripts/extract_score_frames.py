#!/usr/bin/env python3
"""从成片抽取关键帧缩略图，供人工快速验收（title / content / cta）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 各镜大致时间点（秒），无 plan 时用默认
DEFAULT_MARKS = ("1.5", "8.0", "22.0", "32.0")


def _marks_from_plan(task_dir: Path, platform: str) -> list[str]:
    plan_path = task_dir / "llm" / f"slides_render_plan_{platform}.json"
    if not plan_path.is_file():
        return list(DEFAULT_MARKS)
    slides = json.loads(plan_path.read_text(encoding="utf-8-sig")).get("slides") or []
    marks: list[str] = []
    t = 1.0
    for s in slides:
        dur = float(s.get("duration_sec") or s.get("tts_duration_sec") or 5.0)
        marks.append(f"{t + dur * 0.35:.2f}")
        t += dur
    return marks[:6] or list(DEFAULT_MARKS)


def extract_frames(video: Path, out_dir: Path, marks: list[str]) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for i, ts in enumerate(marks):
        out = out_dir / f"frame_{i:02d}_{ts.replace('.', '_')}s.jpg"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            ts,
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out),
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        if r.returncode == 0 and out.is_file():
            written.append(str(out))
    return written


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: extract_score_frames.py <task_dir> [douyin]")
        return 2
    task_dir = Path(sys.argv[1]).resolve()
    platform = (sys.argv[2] if len(sys.argv) > 2 else "douyin").lower()
    video = task_dir / "videos" / f"{platform}.mp4"
    if not video.is_file():
        print(f"missing video: {video}")
        return 1
    marks = _marks_from_plan(task_dir, platform)
    out_dir = task_dir / "quality_frames" / platform
    paths = extract_frames(video, out_dir, marks)
    manifest = {"video": str(video), "frames": paths, "marks_sec": marks}
    manifest_path = task_dir / "QUALITY_FRAMES.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if paths else 1


if __name__ == "__main__":
    raise SystemExit(main())
