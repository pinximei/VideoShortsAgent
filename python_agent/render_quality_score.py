"""抖音成片质量打分（plan + 门禁 + 可选视频，无需 OCR）。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from python_agent.pinned_regression import validate_pinned_douyin_plan


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _video_meta(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False}
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            return {"exists": True, "probe_ok": False}
        data = json.loads(r.stdout or "{}")
        fmt = data.get("format") or {}
        dur = float(fmt.get("duration") or 0)
        vstreams = [s for s in (data.get("streams") or []) if s.get("codec_type") == "video"]
        h = int((vstreams[0] or {}).get("height") or 0) if vstreams else 0
        return {
            "exists": True,
            "probe_ok": True,
            "duration_sec": round(dur, 2),
            "height": h,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return {"exists": True, "probe_ok": False}


def score_douyin_render(
    slides: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
    gate: dict[str, Any] | None = None,
    video_path: Path | None = None,
) -> dict[str, Any]:
    """0–100 分；≥75 且无 error 为 pass。"""
    score = 100
    deductions: list[dict[str, str | int]] = []

    reg = validate_pinned_douyin_plan(slides, brief=brief)
    for err in reg.get("errors") or []:
        score -= 12
        deductions.append({"points": 12, "reason": f"pinned:{err}"})
    for warn in (reg.get("warnings") or [])[:3]:
        score -= 3
        deductions.append({"points": 3, "reason": f"pinned_warn:{warn}"})

    g = gate or {}
    if g.get("errors"):
        score -= 15
        deductions.append({"points": 15, "reason": "quality_gate_error"})
    warn_n = len(g.get("warnings") or [])
    if warn_n:
        pen = min(15, warn_n * 2)
        score -= pen
        deductions.append({"points": pen, "reason": f"quality_warnings:{warn_n}"})

    content = [s for s in slides if s.get("scene_focus") or str(s.get("type")) == "content_card"]
    profiles = {str(s.get("motion_profile") or "") for s in content if str(s.get("motion_profile") or "")}
    if len(content) >= 2 and len(profiles) < 2:
        score -= 8
        deductions.append({"points": 8, "reason": "content_profiles_not_diverse"})

    bound = sum(
        1
        for s in content
        if s.get("_tts_sentences_bound")
        or (isinstance(s.get("summary_reveal_frames"), list) and len(s["summary_reveal_frames"]) >= 3)
    )
    if content and bound < len(content):
        score -= 10
        deductions.append({"points": 10, "reason": "tts_subtitle_not_bound"})

    liquid_n = sum(1 for s in slides if str(s.get("mid_effect") or "") == "liquid_shake")
    if liquid_n > 1:
        score -= 6
        deductions.append({"points": 6, "reason": f"liquid_shake_overuse:{liquid_n}"})

    s0 = slides[0] if slides else {}
    if str(s0.get("type")) == "title_card":
        beats = [str(x).strip() for x in (s0.get("hook_beats") or []) if str(x).strip()]
        if len(beats) < 2:
            score -= 5
            deductions.append({"points": 5, "reason": f"hook_beats_count:{len(beats)}"})

    video_meta: dict[str, Any] = {}
    if video_path:
        video_meta = _video_meta(video_path)
        if not video_meta.get("exists"):
            score -= 20
            deductions.append({"points": 20, "reason": "missing_video"})
        elif video_meta.get("probe_ok"):
            dur = float(video_meta.get("duration_sec") or 0)
            if dur < 12 or dur > 55:
                score -= 8
                deductions.append({"points": 8, "reason": f"duration_out_of_range:{dur}s"})
            if int(video_meta.get("height") or 1920) < 1280:
                score -= 5
                deductions.append({"points": 5, "reason": "low_video_height"})

    frame_audit: dict[str, Any] = {}
    if video_path and video_path.parent.parent.name:
        task_dir = video_path.parent.parent
        if (task_dir / "QUALITY_FRAMES.json").is_file():
            try:
                from python_agent.caption_region_audit import audit_quality_frames

                frame_audit = audit_quality_frames(task_dir, platform="douyin")
                for iss in frame_audit.get("issues") or []:
                    score -= 4
                    deductions.append({"points": 4, "reason": iss})
            except Exception:
                pass

    score = max(0, min(100, score))
    return {
        "platform": "douyin",
        "score": score,
        "grade": _grade(score),
        "deductions": deductions,
        "checks": {
            "pinned_regression": reg,
            "quality_gate_ok": bool(g.get("ok")),
            "content_slides": len(content),
            "tts_bound_slides": bound,
            "liquid_shake_slides": liquid_n,
            "video": video_meta,
            "frame_audit": frame_audit,
        },
        "pass": score >= 75 and not reg.get("errors") and not g.get("errors"),
    }


def score_task(
    task_dir: Path,
    *,
    platform: str = "douyin",
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task_dir = task_dir.resolve()
    plan_path = task_dir / "llm" / f"slides_render_plan_{platform}.json"
    slides: list[dict[str, Any]] = []
    if plan_path.is_file():
        slides = json.loads(plan_path.read_text(encoding="utf-8-sig")).get("slides") or []

    gate_path = task_dir / "llm" / f"slides_quality_gate_{platform}.json"
    gate: dict[str, Any] = {}
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    if brief is None:
        for name in ("brief.json", "BRIEF.json"):
            bp = task_dir / name
            if bp.is_file():
                brief = json.loads(bp.read_text(encoding="utf-8-sig"))
                break

    if platform == "douyin":
        return score_douyin_render(
            slides,
            brief=brief,
            gate=gate,
            video_path=task_dir / "videos" / f"{platform}.mp4",
        )
    return {
        "platform": platform,
        "score": 0,
        "grade": "D",
        "pass": False,
        "deductions": [{"points": 0, "reason": "scoring_only_douyin"}],
        "checks": {},
    }


def write_task_score(
    task_dir: Path,
    *,
    platform: str = "douyin",
    brief: dict[str, Any] | None = None,
) -> Path:
    out = score_task(task_dir, platform=platform, brief=brief)
    path = task_dir.resolve() / "RENDER_QUALITY_SCORE.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
