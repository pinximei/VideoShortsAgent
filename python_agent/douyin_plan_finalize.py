"""抖音分镜终稿：排型表 + 品牌装饰 + 片头钩子（不重复调 LLM shot design）。"""
from __future__ import annotations

import copy
from typing import Any

from python_agent.douyin_layout_registry import (
    CTA_LAYOUT,
    TITLE_LAYOUT,
    css_pack,
    layout_for_content_index,
)
from python_agent.pinned_template import DOUYIN_OPENING_BURST_FRAMES
from python_agent.platform_caption_presets import reconcile_platform_slides
from python_agent.slides_quality_gates import auto_fix_slides


def apply_registry_layout_tiers(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """L00 片头 / L01–L10 内容 / L99 CTA（与十轮排型表一致）。"""
    out: list[dict[str, Any]] = []
    ci = 0
    for s in slides:
        slide = dict(s)
        st = str(slide.get("type") or "")
        if st == "title_card":
            dec = list(slide.get("css_decorations") or [])
            for d in TITLE_LAYOUT["css"]:
                if d not in dec:
                    dec.append(d)
            slide["css_decorations"] = css_pack(dec)
            slide.setdefault("opening_burst", True)
            slide["opening_duration_frames"] = min(
                int(slide.get("opening_duration_frames") or DOUYIN_OPENING_BURST_FRAMES),
                DOUYIN_OPENING_BURST_FRAMES,
            )
        elif st == "cta_card":
            slide["css_decorations"] = list(CTA_LAYOUT["css"])
            slide["motion_profile"] = CTA_LAYOUT["motion_profile"]
            slide["suppress_bottom_caption"] = True
        elif st == "content_card" or slide.get("scene_focus"):
            pack = layout_for_content_index(ci)
            ci += 1
            slide["motion_profile"] = pack["motion_profile"]
            slide["css_decorations"] = list(pack["css"])
            slide.setdefault("mid_effect", pack.get("mid_effect") or "glow_ring")
            slide["mid_info_layout"] = slide.get("mid_info_layout") or (
                "steps" if ci == 0 else "framed" if ci == 1 else "keywords"
            )
            mp = dict(slide.get("motion_params") or {})
            mp["staggerFrames"] = max(14, int(pack.get("stagger_frames") or 14))
            slide["motion_params"] = mp
            dec = [d for d in (slide.get("css_decorations") or []) if d != "corner-brackets"]
            slide["css_decorations"] = dec
            vd = dict(slide.get("visual_design") or {})
            vd["broadcast_frame"] = False
            slide["visual_design"] = vd
        out.append(slide)
    return out


def finalize_douyin_slides(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
    *,
    layout_tiers: bool = True,
) -> list[dict[str, Any]]:
    """Shot design 之后：排型 + 平台 reconcile + auto_fix + 片头钩子。"""
    out = [dict(s) for s in slides]
    if layout_tiers:
        out = apply_registry_layout_tiers(out)

    from python_agent.capabilities.opening_hook import enforce_opening_hook_on_slides_script

    out = list(
        enforce_opening_hook_on_slides_script(
            {"slides": out},
            brief=brief or {},
            platform="douyin",
        ).get("slides")
        or out
    )
    out = reconcile_platform_slides(out, "douyin")
    out = auto_fix_slides(out, platform="douyin", brief=brief)
    from python_agent.douyin_effect_policy import apply_douyin_effect_policy

    out = apply_douyin_effect_policy(out, platform="douyin")
    return out
