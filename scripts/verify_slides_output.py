#!/usr/bin/env python3
"""检查 slides 成片：存在性、分辨率、音轨、时长、质检报告。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _probe(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False}
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return {"exists": True, "probe_error": (r.stderr or "")[-200:]}
    data = json.loads(r.stdout or "{}")
    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})
    dur = float(fmt.get("duration") or 0)
    return {
        "exists": True,
        "bytes": path.stat().st_size,
        "duration_sec": round(dur, 2),
        "width": int(v.get("width") or 0),
        "height": int(v.get("height") or 0),
        "has_audio": bool(a),
        "audio_codec": a.get("codec_name"),
        "video_codec": v.get("codec_name"),
        "ok": dur >= 8 and path.stat().st_size > 80_000 and bool(a) and int(v.get("width") or 0) >= 720,
    }


def verify_task(task_dir: Path) -> dict:
    task_dir = task_dir.resolve()
    out: dict = {"task_dir": str(task_dir), "platforms": {}, "ok": True, "issues": []}

    for plat in ("douyin", "xhs"):
        vid = task_dir / "videos" / f"{plat}.mp4"
        probe = _probe(vid)
        gate_path = task_dir / "llm" / f"slides_quality_gate_{plat}.json"
        gate = {}
        if gate_path.is_file():
            gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))
        plan_path = task_dir / "llm" / f"slides_render_plan_{plat}.json"
        caption_modes = []
        viz_counts: dict[str, int] = {}
        if plan_path.is_file():
            slides = json.loads(plan_path.read_text(encoding="utf-8-sig")).get("slides") or []
            caption_modes = list({s.get("caption_mode") for s in slides})
            for s in slides:
                vt = str(s.get("viz_type") or "none")
                viz_counts[vt] = viz_counts.get(vt, 0) + 1

        row = {
            "video": str(vid),
            "probe": probe,
            "quality_gate": gate,
            "caption_modes": caption_modes,
            "viz_counts": viz_counts,
        }
        out["platforms"][plat] = row
        if not probe.get("ok"):
            out["ok"] = False
            out["issues"].append(f"{plat}: probe_failed {probe}")
        if gate and not gate.get("ok", True):
            out["ok"] = False
            out["issues"].append(f"{plat}: quality_gate {gate.get('errors')}")

    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: py -3 scripts/verify_slides_output.py <task_dir>")
        return 2
    task_dir = Path(sys.argv[1])
    report = verify_task(task_dir)
    out_path = task_dir / "VIDEO_VERIFY_REPORT.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {out_path}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
