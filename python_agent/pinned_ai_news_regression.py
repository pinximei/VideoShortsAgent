"""爱资讯钉死模板 plan 契约（与 GitHub Daily 分离）。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.douyin_news_style import GITHUB_DECOR, is_news_brief
from python_agent.hero_copy import is_generic_hero
from python_agent.pinned_ai_news_template import pick_ai_news_template
from python_agent.pinned_template import DOUYIN_OPENING_BURST_FRAMES, DOUYIN_SUBTITLE_MIN

_BANNED = re.compile(r"star|⭐|开源|仓库|github", re.I)
_NEWS_GENERIC_HERO = frozenset(
    {"核心亮点", "核心能力", "开源神器", "这个仓库", "一步上手", "值得收藏"}
)


def validate_pinned_ai_news_plan(
    slides: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    tmpl = pick_ai_news_template(brief or {})
    template_id = str(tmpl.get("id") or "ai_news_unknown")

    if not slides:
        return {"ok": False, "errors": ["empty_slides"], "warnings": [], "template_id": template_id}

    s0 = slides[0]
    s0_type = str(s0.get("type") or "").strip()
    if s0_type != "title_card" and not (s0.get("hook_text") or s0.get("hook_beats")):
        errors.append("first_slide_not_title")

    if s0_type == "title_card" or s0.get("hook_beats"):
        beats = [str(x).strip() for x in (s0.get("hook_beats") or []) if str(x).strip()]
        for b in beats:
            if _BANNED.search(b):
                errors.append(f"title_hook_github_tone:{b[:12]}")
        if len(beats) < 1:
            errors.append("title_missing_hook_beats")
        if len(beats) > 2:
            warnings.append("title_hook_beats_over_2")
        burst = int(s0.get("opening_duration_frames") or 0)
        if burst > DOUYIN_OPENING_BURST_FRAMES:
            errors.append(f"opening_frames:{burst}>{DOUYIN_OPENING_BURST_FRAMES}")
        dec = set(s0.get("css_decorations") or [])
        if dec & GITHUB_DECOR:
            errors.append(f"title_github_decor:{sorted(dec & GITHUB_DECOR)}")

    content = [s for s in slides if s.get("scene_focus") or str(s.get("type")) == "content_card"]
    if len(content) < 2:
        warnings.append(f"content_slides_low:{len(content)}")

    profiles = {str(s.get("motion_profile") or "") for s in content if s.get("motion_profile")}
    if len(content) >= 2 and len(profiles) < 2:
        warnings.append("content_profiles_not_diverse")

    for i, s in enumerate(content):
        hero = str(s.get("feature_label") or s.get("heading") or "")
        if is_generic_hero(hero) or hero in _NEWS_GENERIC_HERO:
            errors.append(f"content_{i}_generic_hero:{hero}")
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        if len(lines) < DOUYIN_SUBTITLE_MIN:
            errors.append(f"content_{i}_subtitle_count:{len(lines)}<{DOUYIN_SUBTITLE_MIN}")
        tts = str(s.get("tts_text") or "")
        if _BANNED.search(tts):
            errors.append(f"content_{i}_github_tone_tts")
        dec = set(s.get("css_decorations") or [])
        if dec & GITHUB_DECOR:
            errors.append(f"content_{i}_github_decor")

    if str(slides[-1].get("type") or "") != "cta_card":
        warnings.append("last_slide_not_cta")

    pinned_ids = {str(s.get("pinned_ai_news_template_id") or "") for s in slides}
    pinned_ids.discard("")
    if len(pinned_ids) > 1:
        warnings.append("mixed_ai_news_template_ids")

    if brief and not is_news_brief(brief):
        warnings.append("brief_not_news_feed_kind")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "template_id": template_id,
        "template_label": tmpl.get("label"),
        "slide_count": len(slides),
    }


def validate_pinned_plan(
    slides: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """按 feed_kind 路由 GitHub Daily 或爱资讯钉死契约。"""
    if is_news_brief(brief):
        return validate_pinned_ai_news_plan(slides, brief=brief)
    from python_agent.pinned_regression import validate_pinned_douyin_plan

    return validate_pinned_douyin_plan(slides, brief=brief)
