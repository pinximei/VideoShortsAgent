"""pinned 抖音 GitHub Daily 模板 plan 契约回归（不跑 Remotion）。"""
from __future__ import annotations

from typing import Any

from python_agent.hero_copy import is_generic_hero
from python_agent.pinned_template import (
    DOUYIN_OPENING_BURST_FRAMES,
    DOUYIN_SUBTITLE_MAX,
    DOUYIN_SUBTITLE_MIN,
    PINNED_DOUYIN_TEMPLATE_ID,
)


def validate_pinned_douyin_plan(
    slides: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not slides:
        return {"ok": False, "errors": ["empty_slides"], "warnings": [], "template_id": PINNED_DOUYIN_TEMPLATE_ID}

    s0 = slides[0]
    s0_type = str(s0.get("type") or "").strip()
    if s0_type != "title_card":
        if s0.get("hook_text") or s0.get("hook_beats") or s0.get("opening_burst"):
            s0_type = "title_card"
        else:
            errors.append("first_slide_not_title")
    if s0_type == "title_card":
        beats = [str(x).strip() for x in (s0.get("hook_beats") or []) if str(x).strip()]
        if len(beats) < 1:
            errors.append("title_missing_hook_beats")
        if len(beats) > 2:
            warnings.append("title_hook_beats_over_2")
        burst = int(s0.get("opening_duration_frames") or 0)
        if burst > DOUYIN_OPENING_BURST_FRAMES:
            errors.append(f"opening_frames:{burst}>{DOUYIN_OPENING_BURST_FRAMES}")

    content = [s for s in slides if s.get("scene_focus") or str(s.get("type")) == "content_card"]
    if len(content) < 2:
        warnings.append(f"content_slides_low:{len(content)}")

    for i, s in enumerate(content):
        hero = str(s.get("feature_label") or s.get("heading") or "")
        if is_generic_hero(hero):
            errors.append(f"content_{i}_generic_hero:{hero}")
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        if len(lines) < DOUYIN_SUBTITLE_MIN:
            errors.append(f"content_{i}_subtitle_count:{len(lines)}<{DOUYIN_SUBTITLE_MIN}")
        if len(lines) > DOUYIN_SUBTITLE_MAX:
            warnings.append(f"content_{i}_subtitle_count:{len(lines)}>{DOUYIN_SUBTITLE_MAX}")
        reveals = s.get("summary_reveal_frames") or []
        if reveals and reveals != sorted(reveals):
            errors.append(f"content_{i}_reveal_not_monotonic")
        if s.get("_tts_sentences_bound") and not reveals:
            errors.append(f"content_{i}_missing_reveal_frames")

    if str(slides[-1].get("type") or "") != "cta_card":
        warnings.append("last_slide_not_cta")
    elif not slides[-1].get("suppress_bottom_caption"):
        errors.append("cta_missing_suppress_caption")

    fk = str((brief or {}).get("feed_kind") or "").lower()
    if fk in ("github", "github_daily", "daily_github"):
        from python_agent.github_stars_consistency import validate_stars_consistency

        errors.extend(validate_stars_consistency(slides, brief))

    template_id = PINNED_DOUYIN_TEMPLATE_ID
    template_label = ""
    if fk in ("github", "github_daily", "daily_github"):
        from python_agent.pinned_github_template import pick_github_pinned_variant

        pv = pick_github_pinned_variant(brief or {})
        template_id = str(pv.get("id") or template_id)
        template_label = str(pv.get("label") or "")
        pinned_ids = {str(s.get("pinned_github_variant_id") or "") for s in slides}
        pinned_ids.discard("")
        if len(pinned_ids) > 1:
            warnings.append("mixed_github_pinned_variant_ids")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "template_id": template_id,
        "template_label": template_label,
        "slide_count": len(slides),
    }
