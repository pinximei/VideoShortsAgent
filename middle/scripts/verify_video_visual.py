#!/usr/bin/env python3
"""抽帧 + 指标检查成片是否正常（画面推进、有音、分辨率、无黑屏）。"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
    return r.returncode, r.stdout or "", r.stderr or ""


def probe(path: Path) -> dict:
    code, out, _ = run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    if code != 0:
        return {"error": "ffprobe failed"}
    return json.loads(out)


def extract_frame(video: Path, t: float, out: Path) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    code, _, err = run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(t),
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out),
        ],
        timeout=30,
    )
    return code == 0 and out.is_file() and out.stat().st_size > 5000


def file_hash(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def mean_luma(path: Path) -> float:
    """帧平均亮度，黑屏接近 0。"""
    r = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(path),
            "-vf",
            "scale=64:114,format=gray",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-frames:v",
            "1",
            "-",
        ],
        capture_output=True,
        timeout=20,
    )
    if r.returncode != 0 or not r.stdout:
        return -1.0
    data = r.stdout[: 64 * 114]
    if not data:
        return -1.0
    vals = list(data)
    return sum(vals) / len(vals) if vals else 0.0


def check_video(name: str, path: Path, sample_times: list[float]) -> dict:
    report: dict = object()
    issues: list[str] = []
    info = probe(path)
    if info.get("error"):
        return {"name": name, "ok": False, "issues": ["ffprobe 失败"]}

    fmt = info.get("format") or {}
    streams = info.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})

    dur = float(fmt.get("duration") or 0)
    if dur < 5:
        issues.append(f"时长过短 {dur:.1f}s")
    if not a:
        issues.append("无音轨")
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    if w != 1080 or h != 1920:
        issues.append(f"分辨率 {w}x{h} 非竖屏 1080x1920")

    out_dir = ROOT / "data" / "_verify_frames" / name
    hashes: dict[str, str] = {}
    lumas: dict[str, float] = {}
    for t in sample_times:
        if t > dur - 0.1:
            continue
        fp = out_dir / f"t{int(t):03d}.jpg"
        if not extract_frame(path, t, fp):
            issues.append(f"t={t:.0f}s 抽帧失败")
            continue
        hashes[f"{t:.0f}s"] = file_hash(fp)
        lumas[f"{t:.0f}s"] = round(mean_luma(fp), 1)

    unique = len(set(hashes.values()))
    if len(hashes) >= 3 and unique < 2:
        issues.append(f"多时刻画面几乎相同（{unique} 种哈希），B-roll 可能未推进")

    if lumas:
        black = [k for k, v in lumas.items() if v >= 0 and v < 8]
        if len(black) == len(lumas):
            issues.append("各采样帧过暗，可能黑屏")

    return {
        "name": name,
        "ok": len(issues) == 0,
        "duration_s": round(dur, 2),
        "resolution": f"{w}x{h}",
        "audio": a.get("codec_name") if a else None,
        "frame_hashes": hashes,
        "frame_luma": lumas,
        "unique_frames": unique,
        "issues": issues,
    }


def main() -> int:
    task = ROOT / "data/output/838/videos"
    files = {
        "xhs": task / "xhs.mp4",
        "douyin": task / "douyin.mp4",
    }
    reports = []
    for name, p in files.items():
        if not p.is_file():
            print(f"[FAIL] 缺少 {p}", file=sys.stderr)
            return 1
        dur_probe = float((probe(p).get("format") or {}).get("duration") or 50)
        times = [0.5, 5.0, 12.0, 22.0, min(35.0, dur_probe - 1)]
        reports.append(check_video(name, p, times))

    print(json.dumps(reports, ensure_ascii=False, indent=2))
    print(f"\n抽帧目录: {ROOT / 'data' / '_verify_frames'}")
    all_ok = all(r["ok"] for r in reports)
    print("=== 总评 ===")
    print("通过" if all_ok else "存在问题，见各条 issues")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
