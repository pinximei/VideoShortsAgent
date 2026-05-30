"""渲染后特效审计：对比 LLM 分镜与实际 applied effects。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .render_verify import MIN_VIDEO_BYTES


def audit_task_effects(task_dir: Path, platforms: list[str] | None = None) -> dict[str, Any]:
    task_dir = task_dir.resolve()
    plat = platforms or ["douyin", "xhs"]
    report: dict[str, Any] = {"platforms": {}, "ok": True, "warnings": []}

    for pid in plat:
        plan_path = task_dir / "llm" / f"video_clips_{pid}.json"
        applied_path = task_dir / "llm" / f"render_effects_{pid}.json"
        entry: dict[str, Any] = {"has_plan": plan_path.is_file(), "has_applied": applied_path.is_file()}
        mp4 = task_dir / "videos" / f"{pid}.mp4"
        video_ok = mp4.is_file() and mp4.stat().st_size >= MIN_VIDEO_BYTES
        if mp4.is_file():
            entry["video_bytes"] = mp4.stat().st_size

        if not video_ok:
            entry["ok"] = False
            entry["warn"] = "video_missing_or_too_small"
            report["ok"] = False
        else:
            entry["ok"] = True

        if plan_path.is_file() and applied_path.is_file():
            plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
            applied = json.loads(applied_path.read_text(encoding="utf-8-sig"))
            entry["preset_plan"] = (plan.get("effects") or {}).get("preset")
            entry["preset_applied"] = (applied.get("applied_effects") or {}).get("preset")
            entry["gradient_applied"] = (applied.get("applied_effects") or {}).get("gradient")
            entry["transitions"] = applied.get("clip_transitions")
            if not entry["preset_applied"]:
                msg = f"{pid}:missing_preset_after_merge"
                entry["warn"] = msg
                report["warnings"].append(msg)
        elif plan_path.is_file() and not applied_path.is_file():
            msg = f"{pid}:render_effects_missing"
            entry["warn"] = msg
            report["warnings"].append(msg)

        report["platforms"][pid] = entry

    audit_path = task_dir / "effects_audit.json"
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
