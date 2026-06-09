"""GitHub Daily 终稿：钉死三款式衍生 + shot 之后覆盖排型表（避免全站同一 L 槽）。"""
from __future__ import annotations

from typing import Any

from python_agent.douyin_effect_policy import apply_douyin_effect_policy
from python_agent.douyin_plan_finalize import apply_registry_layout_tiers
from python_agent.motion_templates import is_github_daily_brief
from python_agent.pinned_github_template import (
    apply_pinned_github_plan,
    inject_github_pinned_brief,
    pick_github_pinned_variant,
)
from python_agent.platform_caption_presets import reconcile_platform_slides
from python_agent.slides_quality_gates import auto_fix_slides


def finalize_douyin_github_slides(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
    *,
    layout_tiers: bool = False,
) -> list[dict[str, Any]]:
    if not is_github_daily_brief(brief):
        return slides
    b = inject_github_pinned_brief(dict(brief or {}))
    tmpl = pick_github_pinned_variant(b)
    out = apply_pinned_github_plan([dict(s) for s in slides], b, tmpl)

    from python_agent.capabilities.opening_hook import enforce_opening_hook_on_slides_script

    out = list(
        enforce_opening_hook_on_slides_script(
            {"slides": out},
            brief=b,
            platform="douyin",
        ).get("slides")
        or out
    )
    if layout_tiers:
        out = apply_registry_layout_tiers(out, b)
    out = reconcile_platform_slides(out, "douyin")
    out = auto_fix_slides(out, platform="douyin", brief=b)
    out = apply_douyin_effect_policy(out, platform="douyin")
    out = apply_pinned_github_plan(out, b, tmpl)
    return out
