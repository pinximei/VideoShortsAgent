#!/usr/bin/env python3
"""生成竖屏 B-roll 占位（深色底 + 弱动效彩条，优于纯 testsrc2）。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "assets" / "broll_template.mp4"


def ensure_broll(path: Path, *, seconds: float = 60.0, force: bool = False) -> Path:
    path = path.resolve()
    if path.is_file() and path.stat().st_size > 50000 and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    # 深蓝底 + 半透明 testsrc2 叠加，竖屏 1080x1920
    fc = (
        "[0][1]blend=all_mode=overlay:all_opacity=0.28[v];"
        "[v]noise=alls=8:allf=t+u,eq=brightness=0.02:saturation=1.05[outv]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0f172a:s=1080x1920:d={seconds}:r=30",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size=1080x1920:rate=30",
        "-filter_complex",
        fc,
        "-map",
        "[outv]",
        "-t",
        str(seconds),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "fast",
        str(path),
    ]
    print(f"[ensure_broll] 生成 {path} ({seconds}s)")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {(r.stderr or '')[-500:]}")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default=str(DEFAULT_OUT))
    ap.add_argument("-t", "--seconds", type=float, default=60.0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ensure_broll(Path(args.output), seconds=args.seconds, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
