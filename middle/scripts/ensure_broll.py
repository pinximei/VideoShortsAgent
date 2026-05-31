#!/usr/bin/env python3
"""生成竖屏 B-roll：深色渐变 + 轻微 Ken Burns（禁止 testsrc2 彩条）。"""
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
    # 深蓝竖屏底 + 极弱噪点 + 缓慢推镜（无 testsrc2，避免竖条/棋盘格）
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "zoompan=z='min(zoom+0.0006,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,"
        "noise=alls=6:allf=t+u,eq=brightness=-0.03:saturation=0.92:contrast=1.05,"
        "vignette=PI/5[outv]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0f172a:s=1080x1920:r=30:d={seconds}",
        "-vf",
        vf,
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
        "-movflags",
        "+faststart",
        str(path),
    ]
    print(f"[ensure_broll] 生成 cinematic B-roll → {path} ({seconds}s)")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        # 降级：纯色 + 轻噪点（仍不用 testsrc2）
        fallback_vf = (
            "scale=1080:1920,format=yuv420p,"
            "noise=alls=5:allf=t+u,eq=brightness=-0.02:saturation=0.9"
        )
        cmd2 = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x0f172a:s=1080x1920:d={seconds}:r=30",
            "-vf",
            fallback_vf,
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
        r = subprocess.run(cmd2, capture_output=True, text=True, timeout=180)
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
