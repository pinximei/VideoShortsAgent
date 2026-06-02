"""离线单变量 A/B：只改 plan 参数，打分选优（不重新 TTS/Remotion）。"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from python_agent.pinned_template import DOUYIN_OPENING_BURST_FRAMES
from python_agent.render_quality_score import score_douyin_render
from python_agent.slides_quality_gates import auto_fix_slides, validate_slides_before_render

SlideList = list[dict[str, Any]]
VariantFn = Callable[[SlideList], SlideList]


def _bump_mp(slides: SlideList, **kwargs: Any) -> SlideList:
    out: list[dict[str, Any]] = []
    for s in slides:
        slide = dict(s)
        mp = dict(slide.get("motion_params") or {})
        mp.update(kwargs)
        slide["motion_params"] = mp
        out.append(slide)
    return out


def _variant_baseline(slides: SlideList) -> SlideList:
    return [dict(s) for s in slides]


def _variant_caption_lower(slides: SlideList) -> SlideList:
    return _bump_mp(slides, captionBottomPx=270, midSafeBottomRatio=0.34)


def _variant_caption_standard(slides: SlideList) -> SlideList:
    return _bump_mp(slides, captionBottomPx=300, midSafeBottomRatio=0.40)


def _variant_stagger_fast(slides: SlideList) -> SlideList:
    return _bump_mp(slides, staggerFrames=12)


def _variant_opening_tight(slides: SlideList) -> SlideList:
    out = [dict(s) for s in slides]
    if out and str(out[0].get("type")) == "title_card":
        out[0]["opening_duration_frames"] = DOUYIN_OPENING_BURST_FRAMES
    return out


PLAN_VARIANTS: list[tuple[str, VariantFn]] = [
    ("baseline", _variant_baseline),
    ("caption_lower", _variant_caption_lower),
    ("caption_standard", _variant_caption_standard),
    ("stagger_fast", _variant_stagger_fast),
    ("opening_tight", _variant_opening_tight),
]


def evaluate_variant(
    slides: SlideList,
    variant_id: str,
    apply_fn: VariantFn,
    *,
    brief: dict[str, Any] | None = None,
    video_path: Path | None = None,
) -> dict[str, Any]:
    trial = apply_fn(copy.deepcopy(slides))
    trial = auto_fix_slides(trial, platform="douyin", brief=brief)
    from python_agent.layout_collision import fix_all_layout_collisions

    trial = fix_all_layout_collisions(trial)
    gate = validate_slides_before_render(trial, platform="douyin", brief=brief)
    score = score_douyin_render(
        trial,
        brief=brief,
        gate=gate,
        video_path=video_path,
    )
    return {
        "variant_id": variant_id,
        "gate_ok": bool(gate.get("ok")),
        "gate_errors": gate.get("errors") or [],
        "score": score,
    }


def run_offline_loop(
    task_dir: Path,
    *,
    brief: dict[str, Any] | None = None,
    include_video: bool = False,
) -> tuple[dict[str, Any], SlideList]:
    task_dir = task_dir.resolve()
    plan_path = task_dir / "llm" / "slides_render_plan_douyin.json"
    if not plan_path.is_file():
        raise FileNotFoundError(f"missing plan: {plan_path}")
    slides = json.loads(plan_path.read_text(encoding="utf-8-sig")).get("slides") or []
    if brief is None and (task_dir / "brief.json").is_file():
        brief = json.loads((task_dir / "brief.json").read_text(encoding="utf-8-sig"))

    video = task_dir / "videos" / "douyin.mp4" if include_video else None
    if video and not video.is_file():
        video = None

    results: list[dict[str, Any]] = []
    for vid, fn in PLAN_VARIANTS:
        results.append(
            evaluate_variant(
                slides,
                vid,
                fn,
                brief=brief,
                video_path=video,
            )
        )

    passing = [r for r in results if r.get("gate_ok") and (r.get("score") or {}).get("pass")]
    pool = passing or [r for r in results if r.get("gate_ok")] or results
    best = max(
        pool,
        key=lambda r: int((r.get("score") or {}).get("score") or 0),
    )
    best_id = str(best.get("variant_id") or "baseline")
    best_fn = next((fn for vid, fn in PLAN_VARIANTS if vid == best_id), _variant_baseline)
    recommended = auto_fix_slides(
        best_fn(copy.deepcopy(slides)),
        platform="douyin",
        brief=brief,
    )

    from python_agent.caption_region_audit import audit_task_caption_region

    caption_audit = audit_task_caption_region(task_dir, platform="douyin")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_dir": str(task_dir),
        "best_variant": best_id,
        "results": results,
        "caption_audit": caption_audit,
        "recommended_applied": False,
    }
    return report, recommended


def write_offline_loop_report(
    task_dir: Path,
    *,
    brief: dict[str, Any] | None = None,
    apply_best: bool = False,
    include_video: bool = False,
) -> Path:
    report, recommended = run_offline_loop(
        task_dir,
        brief=brief,
        include_video=include_video,
    )
    if apply_best:
        plan_path = task_dir / "llm" / "slides_render_plan_douyin.json"
        plan_path.write_text(
            json.dumps({"slides": recommended, "platform": "douyin"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report["recommended_applied"] = True
    out_path = task_dir / "OFFLINE_LOOP_REPORT.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
