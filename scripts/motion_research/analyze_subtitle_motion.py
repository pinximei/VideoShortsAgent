#!/usr/bin/env python3
"""
从参考视频底部字幕区提取帧差，估计「字幕切换间隔 / 运动强度」。

不依赖 OpenCV，仅用 ffmpeg + Pillow。
输出 JSON 报告供动效参数校准（wordsPerPageMs、stagger 等）。
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "research" / "motion" / "reports"


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{p.stderr}")


def probe_duration(video: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return float(p.stdout.strip())


def extract_frames(video: Path, frames_dir: Path, *, fps: float = 5.0) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = frames_dir / "f_%05d.png"
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"fps={fps}",
            "-q:v",
            "2",
            str(pattern),
        ]
    )
    return sorted(frames_dir.glob("f_*.png"))


def crop_subtitle_band(img: Image.Image, *, top_ratio: float = 0.62) -> Image.Image:
    w, h = img.size
    y0 = int(h * top_ratio)
    return img.crop((0, y0, w, h)).convert("L").resize((320, 120))


def frame_diff(a: Image.Image, b: Image.Image) -> float:
    pa, pb = a.load(), b.load()
    w, h = a.size
    total = 0
    for y in range(h):
        for x in range(w):
            total += abs(pa[x, y] - pb[x, y])
    return total / (w * h * 255.0)


def detect_peaks(diffs: list[float], *, threshold: float) -> list[int]:
    if not diffs:
        return []
    mu = sum(diffs) / len(diffs)
    sigma = math.sqrt(sum((d - mu) ** 2 for d in diffs) / max(1, len(diffs) - 1))
    cut = max(threshold, mu + 1.2 * sigma)
    peaks: list[int] = []
    for i, d in enumerate(diffs):
        if d >= cut and (i == 0 or d > diffs[i - 1]):
            if not peaks or i - peaks[-1] > 2:
                peaks.append(i)
    return peaks


def analyze(video: Path, *, sample_fps: float = 5.0) -> dict:
    duration = probe_duration(video)
    work = video.parent / f"_frames_{video.stem}"
    if work.exists():
        for f in work.glob("f_*.png"):
            f.unlink()
    else:
        work.mkdir(parents=True, exist_ok=True)

    paths = extract_frames(video, work, fps=sample_fps)
    bands = [crop_subtitle_band(Image.open(p)) for p in paths]
    diffs = [frame_diff(bands[i - 1], bands[i]) for i in range(1, len(bands))]
    peaks = detect_peaks(diffs, threshold=0.04)

    intervals_sec: list[float] = []
    for i in range(1, len(peaks)):
        intervals_sec.append((peaks[i] - peaks[0]) / sample_fps)
    if len(peaks) >= 2:
        gaps = [(peaks[i] - peaks[i - 1]) / sample_fps for i in range(1, len(peaks))]
        median_gap = sorted(gaps)[len(gaps) // 2]
    else:
        median_gap = None

    motion_mean = sum(diffs) / len(diffs) if diffs else 0.0
    motion_max = max(diffs) if diffs else 0.0

    return {
        "video": str(video.resolve()),
        "duration_sec": round(duration, 2),
        "sample_fps": sample_fps,
        "frames_analyzed": len(paths),
        "subtitle_band": "bottom 38% (y>62%)",
        "motion_mean_diff": round(motion_mean, 4),
        "motion_max_diff": round(motion_max, 4),
        "change_peaks_count": len(peaks),
        "estimated_switch_interval_sec": round(median_gap, 2) if median_gap else None,
        "estimated_switch_interval_ms": int(median_gap * 1000) if median_gap else None,
        "suggested_combine_tokens_ms": int(median_gap * 1000)
        if median_gap and median_gap < 3
        else 1200,
        "peak_indices": peaks[:30],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze subtitle-region motion in reference videos")
    ap.add_argument("videos", nargs="+", type=Path, help="Reference mp4 files")
    ap.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fps", type=float, default=5.0)
    args = ap.parse_args()

    reports: list[dict] = []
    for v in args.videos:
        if not v.is_file():
            print(f"skip missing: {v}", file=sys.stderr)
            continue
        print(f"[analyze] {v.name} …")
        reports.append(analyze(v.resolve(), sample_fps=args.fps))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "analyze_subtitle_motion.py",
        "reports": reports,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / f"subtitle_motion_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    for r in reports:
        print(
            f"  {Path(r['video']).name}: peaks={r['change_peaks_count']} "
            f"switch≈{r.get('estimated_switch_interval_ms')}ms "
            f"suggest combineTokens={r.get('suggested_combine_tokens_ms')}ms"
        )
    return 0 if reports else 1


if __name__ == "__main__":
    raise SystemExit(main())
