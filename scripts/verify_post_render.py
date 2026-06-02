#!/usr/bin/env python3
"""成片后门禁：plan 契约、平台差异、叠字启发式、时长。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_plan(task_dir: Path, plat: str) -> list[dict]:
    p = task_dir / "llm" / f"slides_render_plan_{plat}.json"
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8-sig")).get("slides") or []


def _plan_checks(slides: list[dict], plat: str) -> list[str]:
    issues: list[str] = []
    if not slides:
        return [f"{plat}:missing_plan"]
    content = [s for s in slides if s.get("scene_focus") or str(s.get("type")) == "content_card"]
    if plat == "xhs":
        if not any(str(s.get("caption_mode")) == "editorial" for s in slides):
            issues.append(f"{plat}:caption_not_editorial")
        for s in content:
            if (s.get("visual_design") or {}).get("broadcast_frame"):
                issues.append(f"{plat}:content_broadcast_frame")
            bg = str(s.get("background_color") or "").lower()
            if bg and not bg.startswith("#f"):
                issues.append(f"{plat}:content_bg_not_light:{bg}")
    if plat == "douyin":
        if not any(str(s.get("caption_mode")) == "tiktok" for s in slides):
            issues.append(f"{plat}:caption_not_tiktok")
    profiles = {str(s.get("motion_profile") or "") for s in content}
    if len(content) >= 2 and len(profiles) < 2:
        issues.append(f"{plat}:content_profiles_not_diverse")
    kv_body = 0
    for s in slides:
        body = "\n".join(
            [
                str(s.get("heading") or ""),
                " ".join(str(x) for x in (s.get("summary_lines") or [])),
            ]
        )
        if re.search(r"产品\s*[:：]", body) and re.search(r"标语\s*[:：]", body):
            kv_body += 1
    if kv_body:
        issues.append(f"{plat}:connector_kv_in_slides")
    viz = sum(1 for s in content if str(s.get("viz_type") or "none") != "none")
    stat_in_cards = any(
        "star" in str(x).lower() or "⭐" in str(x) or "星" in str(x)
        for s in content
        for x in (s.get("summary_lines") or [])
    )
    card_only = plat == "douyin" and (
        profiles <= {"glass_card_stack", ""} or len(profiles) >= 2
    )
    if content and viz < 1 and not stat_in_cards and not card_only:
        issues.append(f"{plat}:no_viz_on_content")
    return issues


def _duration_skew(douyin: float, xhs: float) -> list[str]:
    issues: list[str] = []
    if douyin <= 0 or xhs <= 0:
        return issues
    ratio = abs(xhs - douyin) / min(douyin, xhs)
    if ratio > 0.22:
        issues.append(f"duration_skew:{douyin:.1f}s_vs_{xhs:.1f}s")
    if douyin > 52 or xhs > 58:
        issues.append(f"duration_too_long:d={douyin:.1f},x={xhs:.1f}")
    return issues


def verify_post_render(task_dir: Path, *, report: dict | None = None) -> dict:
    task_dir = task_dir.resolve()
    issues: list[str] = []
    report = report or {}
    platforms = report.get("platforms") or {}
    for plat in (report.get("platforms") or {}).keys() or ("douyin", "xhs"):
        issues.extend(_plan_checks(_load_plan(task_dir, plat), plat))
    d_dur = float((platforms.get("douyin") or {}).get("duration_sec") or 0)
    x_dur = float((platforms.get("xhs") or {}).get("duration_sec") or 0)
    issues.extend(_duration_skew(d_dur, x_dur))
    modes_d = set(_load_plan(task_dir, "douyin") and [str(s.get("caption_mode")) for s in _load_plan(task_dir, "douyin")] or [])
    modes_x = set(_load_plan(task_dir, "xhs") and [str(s.get("caption_mode")) for s in _load_plan(task_dir, "xhs")] or [])
    if modes_d and modes_x and modes_d == modes_x:
        issues.append("caption_modes_identical")
    return {"ok": not issues, "issues": issues}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: verify_post_render.py <task_dir> [VERIFY_REPORT.json]")
        return 2
    task_dir = Path(sys.argv[1])
    report: dict = {}
    if len(sys.argv) >= 3:
        report = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8-sig"))
    elif (task_dir.parent / "VERIFY_REPORT.json").is_file():
        report = json.loads((task_dir.parent / "VERIFY_REPORT.json").read_text(encoding="utf-8-sig"))
    out = verify_post_render(task_dir, report=report)
    path = task_dir / "POST_RENDER_VERIFY.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
