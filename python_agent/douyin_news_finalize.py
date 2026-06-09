"""爱资讯终稿：钉死多款式模板 + 平台 reconcile + 门禁（不走 GitHub shot LLM）。"""
from __future__ import annotations

from typing import Any

from python_agent.douyin_effect_policy import apply_douyin_effect_policy
from python_agent.douyin_news_style import (
    apply_douyin_news_style,
    enforce_ai_news_cta_slide,
    enforce_ai_news_product_clarity,
    is_news_brief,
)
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
    from python_agent.pinned_ai_news_template import inject_ai_news_pinned_brief

    b = inject_ai_news_pinned_brief(b)
    tmpl = pick_ai_news_template(b)

    out = normalize_slide_types([dict(s) for s in slides])
    out = apply_pinned_ai_news_plan(out, b, tmpl)

    from python_agent.ai_news_visual import apply_variant_visual_dna

    out = apply_variant_visual_dna(out, tmpl)

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
    out = enforce_ai_news_product_clarity(out, b)
    out = enforce_ai_news_cta_slide(out, b)
    out = _lock_news_anchor_tts_on_slides(out, b)
    out = apply_douyin_news_style(out, b)
    from python_agent.platform_traffic_rules import sanitize_slides_traffic

    return sanitize_slides_traffic(out)


def _lock_news_anchor_tts_on_slides(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """全片统一口播参数，避免某镜自带 tts_rate 导致语速忽快忽慢。"""
    if not is_news_brief(brief):
        return slides
    out: list[dict[str, Any]] = []
    for s in slides:
        row = dict(s)
        row.pop("tts_rate", None)
        row.pop("tts_pitch", None)
        row.pop("sentence_pause_sec", None)
        row["_news_anchor_pace"] = True
        out.append(row)
    return out


def ai_news_visual_style(brief: dict[str, Any] | None) -> str:
    return str(pick_ai_news_template(brief or {}).get("visual_style") or "warm_gold")
