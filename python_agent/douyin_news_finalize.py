"""爱资讯终稿：钉死多款式模板 + 平台 reconcile + 门禁（不走 GitHub shot LLM）。"""
from __future__ import annotations

from typing import Any

from python_agent.douyin_effect_policy import apply_douyin_effect_policy
from python_agent.douyin_news_style import apply_douyin_news_style, is_news_brief
from python_agent.pinned_ai_news_template import apply_pinned_ai_news_plan, pick_ai_news_template
from python_agent.platform_caption_presets import reconcile_platform_slides
from python_agent.slide_type_normalize import normalize_slide_types
from python_agent.slides_quality_gates import auto_fix_slides


def finalize_douyin_news_slides(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not is_news_brief(brief):
        return slides
    b = dict(brief or {})
    tmpl = pick_ai_news_template(b)
    b["pinned_ai_news_template_id"] = tmpl.get("id")
    b["ai_news_visual_style"] = tmpl.get("visual_style")
    b["compose_template_hint"] = tmpl.get("compose_hint") or ""

    out = normalize_slide_types([dict(s) for s in slides])
    out = apply_pinned_ai_news_plan(out, b, tmpl)

    from python_agent.capabilities.opening_hook import enforce_opening_hook_on_slides_script

    out = list(
        enforce_opening_hook_on_slides_script(
            {"slides": out},
            brief=b,
            platform="douyin",
        ).get("slides")
        or out
    )
    out = reconcile_platform_slides(out, "douyin")
    out = auto_fix_slides(out, platform="douyin", brief=b)
    out = apply_douyin_effect_policy(out, platform="douyin")
    out = apply_pinned_ai_news_plan(out, b, tmpl)
    out = apply_douyin_news_style(out, b)
    return out


def ai_news_visual_style(brief: dict[str, Any] | None) -> str:
    return str(pick_ai_news_template(brief or {}).get("visual_style") or "warm_gold")
