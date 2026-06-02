"""底栏字幕区启发式验收（plan 碰撞 + 可选抽帧）。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from python_agent.layout_collision import check_slide_layout_collision


def plan_caption_risks(slides: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for i, s in enumerate(slides):
        if not (s.get("scene_focus") or str(s.get("type")) == "content_card"):
            continue
        coll = check_slide_layout_collision(s)
        if not coll.get("ok"):
            gap = int(coll.get("gap_px") or -999)
            issues.append(f"slide_{i}:gap={gap}px:{','.join(coll.get('issues') or [])}")
    return issues


def _frame_bottom_luma(frame: Path) -> float | None:
    """底 22% 区域平均亮度（0–255），需 ffmpeg。"""
    vf = "crop=iw:ih*0.22:0:ih*0.72,format=gray,signalstats"
    try:
        r = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(frame),
                "-vf",
                vf,
                "-frames:v",
                "1",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=25,
        )
        blob = (r.stderr or "") + (r.stdout or "")
        for line in blob.splitlines():
            if "YAVG" in line:
                parts = line.split(":")
                for p in parts:
                    try:
                        return float(p.strip())
                    except ValueError:
                        continue
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    return None


def audit_quality_frames(task_dir: Path, *, platform: str = "douyin") -> dict[str, Any]:
    manifest_path = task_dir / "QUALITY_FRAMES.json"
    if not manifest_path.is_file():
        return {"ok": True, "skipped": True, "reason": "no_quality_frames"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    frames = [Path(p) for p in (manifest.get("frames") or []) if Path(p).is_file()]
    if not frames:
        return {"ok": False, "issues": ["no_frame_files"]}
    lumas: list[float] = []
    issues: list[str] = []
    for fp in frames:
        y = _frame_bottom_luma(fp)
        if y is None:
            continue
        lumas.append(y)
        if y > 200:
            issues.append(f"bright_caption_band:{fp.name}:{y:.0f}")
    return {
        "ok": not issues,
        "frame_count": len(frames),
        "lumas": [round(x, 1) for x in lumas],
        "issues": issues,
    }


def audit_task_caption_region(task_dir: Path, *, platform: str = "douyin") -> dict[str, Any]:
    task_dir = task_dir.resolve()
    plan_path = task_dir / "llm" / f"slides_render_plan_{platform}.json"
    slides: list[dict[str, Any]] = []
    if plan_path.is_file():
        slides = json.loads(plan_path.read_text(encoding="utf-8-sig")).get("slides") or []
    plan_issues = plan_caption_risks(slides)
    frame_audit = audit_quality_frames(task_dir, platform=platform)
    ok = not plan_issues and frame_audit.get("ok", True)
    return {
        "ok": ok,
        "plan_risks": plan_issues,
        "frames": frame_audit,
    }
