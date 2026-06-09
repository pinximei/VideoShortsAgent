"""GitHub Daily 钉死模板族：v1 基线的三款式衍生（与爱资讯 catalog 同模式）。"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from python_agent.ai_news_visual import apply_variant_visual_dna
from python_agent.motion_templates import is_github_daily_brief
from python_agent.pinned_template import DOUYIN_OPENING_BURST_FRAMES, DOUYIN_MAX_HOOK_BEATS

_CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "pinned_douyin_github_daily"
    / "catalog.json"
)
PINNED_GITHUB_FAMILY = "douyin_github_daily"
PINNED_GITHUB_BASE_ID = "douyin_github_daily_v1"


@lru_cache(maxsize=1)
def load_github_pinned_catalog() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {"variants": []}
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def list_github_pinned_variants() -> list[dict[str, Any]]:
    return list(load_github_pinned_catalog().get("variants") or [])


def _seed_int(key: str) -> int:
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def pick_github_pinned_variant(brief: dict[str, Any]) -> dict[str, Any]:
    """按 content_key / article_id 稳定轮换（与 G20 哈希独立，优先本族三款式）。"""
    variants = list_github_pinned_variants()
    if not variants:
        return {
            "id": "github_daily_fallback",
            "label": "GitHub 默认",
            "gv": {"motion_id": "G01_cyber_hook_yellow", "voice_id": "V01_burst_hook_fast"},
            "gradient_colors": ["#0d1117", "#1a1033"],
            "content_slots": [],
            "title": {"motion_profile": "github_daily_hook", "css": []},
            "cta": {"motion_profile": "cta_pulse_arrow", "css": []},
            "opening": {"duration_frames": 84},
            "caption": {},
        }
    explicit = str(brief.get("pinned_github_variant_id") or "").strip()
    if explicit:
        for v in variants:
            if v.get("id") == explicit:
                return dict(v)
    seed = str(
        brief.get("content_key")
        or brief.get("article_id")
        or brief.get("repo_name")
        or brief.get("title")
        or "github_daily"
    )
    idx = _seed_int(seed) % len(variants)
    return dict(variants[idx])


def inject_github_pinned_brief(brief: dict[str, Any]) -> dict[str, Any]:
    """写入款式 id 与 G/V，关闭平台默认 G01 锁死。"""
    if not is_github_daily_brief(brief):
        return brief
    b = dict(brief)
    tmpl = pick_github_pinned_variant(b)
    b["pinned_github_variant_id"] = tmpl.get("id")
    b["github_pinned_visual_style"] = tmpl.get("visual_style")
    b["use_platform_gv_default"] = False
    gv = dict(tmpl.get("gv") or {})
    if gv.get("motion_id"):
        b["github_daily_style_id"] = str(gv["motion_id"])
    if gv.get("voice_id"):
        b["voice_content_style_id"] = str(gv["voice_id"])
    return b


def apply_pinned_github_plan(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
    template: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """套用钉死 GitHub 衍生款式（保留 Star/角标类装饰）。"""
    if not is_github_daily_brief(brief):
        return slides
    tmpl = template or pick_github_pinned_variant(brief)
    tid = str(tmpl.get("id") or "github_daily_unknown")
    title_cfg = tmpl.get("title") or {}
    cta_cfg = tmpl.get("cta") or {}
    slots = list(tmpl.get("content_slots") or [])
    opening = tmpl.get("opening") or {}
    cap = tmpl.get("caption") or {}
    grad = list(tmpl.get("gradient_colors") or ["#0d1117", "#1a1033"])

    staged = apply_variant_visual_dna([dict(s) for s in slides], tmpl)
    out: list[dict[str, Any]] = []
    ci = 0
    for s in staged:
        slide = dict(s)
        st = str(slide.get("type") or "")
        slide["pinned_github_variant_id"] = tid
        slide["github_pinned_family"] = PINNED_GITHUB_FAMILY

        if st == "title_card":
            slide["motion_profile"] = title_cfg.get("motion_profile") or slide.get(
                "motion_profile"
            ) or "github_daily_hook"
            dec = list(slide.get("css_decorations") or [])
            for d in title_cfg.get("css") or []:
                if d not in dec:
                    dec.append(d)
            slide["css_decorations"] = dec
            slide["background_color"] = grad[0]
            slide["opening_burst"] = True
            burst = int(opening.get("duration_frames") or DOUYIN_OPENING_BURST_FRAMES)
            slide["opening_duration_frames"] = min(burst, DOUYIN_OPENING_BURST_FRAMES)
            slide["caption_mode"] = cap.get("mode") or "tiktok"
            gv = dict(tmpl.get("gv") or {})
            if gv.get("motion_id"):
                slide["github_daily_style_id"] = str(gv["motion_id"])
        elif st == "cta_card":
            slide["motion_profile"] = cta_cfg.get("motion_profile") or "cta_pulse_arrow"
            dec = list(slide.get("css_decorations") or [])
            for d in cta_cfg.get("css") or []:
                if d not in dec:
                    dec.append(d)
            slide["css_decorations"] = dec
            slide["suppress_bottom_caption"] = True
            slide["mid_info_layout"] = "none"
            slide["viz_type"] = "none"
        elif st == "content_card" or slide.get("scene_focus"):
            slide["type"] = "content_card"
            slot = slots[ci % len(slots)] if slots else {}
            ci += 1
            si = (ci - 1) % max(len(grad), 1)
            slide["background_color"] = grad[si % len(grad)]
            slide["motion_profile"] = slot.get("motion_profile") or slide.get(
                "motion_profile"
            ) or "github_daily_bullets"
            dec = list(slide.get("css_decorations") or [])
            for d in slot.get("css") or []:
                if d not in dec:
                    dec.append(d)
            slide["css_decorations"] = dec
            slide["mid_effect"] = slot.get("mid_effect") or slide.get("mid_effect") or "glow_ring"
            slide["mid_info_layout"] = slot.get("mid_info_layout") or slide.get(
                "mid_info_layout"
            ) or "framed"
            mp = dict(slide.get("motion_params") or {})
            mp["staggerFrames"] = min(16, max(14, int(mp.get("staggerFrames") or 14)))
            mp["maxCharsPerPage"] = int(cap.get("max_chars_per_page") or 24)
            mp["captionBottomPx"] = int(cap.get("caption_bottom_px") or 300)
            mp["midSafeBottomRatio"] = float(cap.get("mid_safe_bottom_ratio") or 0.42)
            slide["motion_params"] = mp
            slide.pop("opening_duration_frames", None)
        out.append(slide)
    return out
