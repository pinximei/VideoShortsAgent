"""爱资讯钉死模板族：多款式轮换（与 GitHub Daily 分离）。"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from python_agent.douyin_news_style import GITHUB_DECOR, is_news_brief
from python_agent.pinned_template import DOUYIN_MAX_HOOK_BEATS, DOUYIN_OPENING_BURST_FRAMES

_CATALOG_PATH = (
    Path(__file__).resolve().parents[1] / "templates" / "pinned_douyin_ai_news" / "catalog.json"
)
PINNED_AI_NEWS_FAMILY = "douyin_ai_news"

# 爱资讯抖音量产固定款（config.yaml 默认与此一致；勿随机轮换）
PINNED_AI_NEWS_PRODUCTION_TEMPLATE_ID = "ai_news_void_signal"
PINNED_AI_NEWS_PRODUCTION_LABEL = "虚空信号·黑金专线"

_BANNED_NEWS_COPY = re.compile(
    r"star|⭐|开源|仓库|github|点个star|mit\s*协议|readme",
    re.I,
)


@lru_cache(maxsize=1)
def load_ai_news_catalog() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {"variants": []}
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def reload_ai_news_catalog() -> None:
    load_ai_news_catalog.cache_clear()


def list_ai_news_variants(*, tier: str | None = None) -> list[dict[str, Any]]:
    raw = list(load_ai_news_catalog().get("variants") or [])
    if not tier:
        return raw
    return [v for v in raw if str(v.get("tier") or "base") == tier]


def list_ai_news_bases() -> list[dict[str, Any]]:
    return list_ai_news_variants(tier="base")


# 默认轮换时排除：白底、大红、晨报浅色
_DEFAULT_EXCLUDED_TEMPLATE_IDS = frozenset(
    {
        "ai_news_inferno_alert",
        "ai_news_inferno_alert_snap",
        "ai_news_inferno_alert_rush",
        "ai_news_glacier_wire",
        "ai_news_glacier_wire_snap",
        "ai_news_glacier_wire_rush",
        "ai_news_morning_paper",
        "ai_news_morning_paper_snap",
        "ai_news_morning_paper_rush",
        "ai_news_coral_bloom",
        "ai_news_coral_bloom_snap",
        "ai_news_coral_bloom_rush",
        "ai_news_prism_scan",
        "ai_news_prism_scan_snap",
        "ai_news_prism_scan_rush",
    }
)


def _rotation_pool(brief: dict[str, Any]) -> list[dict[str, Any]]:
    pool_key = str(brief.get("ai_news_rotation_pool") or "base").strip().lower()
    if pool_key in ("all", "full", "27"):
        raw = list_ai_news_variants()
    elif pool_key == "derivative":
        raw = list_ai_news_variants(tier="derivative")
    else:
        raw = list_ai_news_bases()
    excluded = set(_DEFAULT_EXCLUDED_TEMPLATE_IDS)
    extra = brief.get("ai_news_exclude_template_ids") or []
    if isinstance(extra, str):
        extra = [x.strip() for x in extra.split(",") if x.strip()]
    excluded.update(str(x) for x in extra)
    return [v for v in raw if v.get("id") not in excluded]


def _seed_int(key: str) -> int:
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def inject_ai_news_pinned_brief(brief: dict[str, Any]) -> dict[str, Any]:
    """写入钉死款式 id / 口播 / 轮换池（显式 id 时不改 pool）。"""
    if not is_news_brief(brief):
        return brief
    b = dict(brief)
    tmpl = pick_ai_news_template(b)
    b["pinned_ai_news_template_id"] = tmpl.get("id")
    b["ai_news_visual_style"] = tmpl.get("visual_style")
    from python_agent.tts_voice_presets import DEFAULT_NEWS_PRESET_ID

    b.setdefault("tts_voice_preset", DEFAULT_NEWS_PRESET_ID)
    if tmpl.get("compose_hint"):
        b["compose_template_hint"] = str(tmpl["compose_hint"])
    if tmpl.get("parent_id"):
        b["ai_news_parent_template_id"] = str(tmpl["parent_id"])
    return b


def pick_ai_news_template(brief: dict[str, Any]) -> dict[str, Any]:
    """按 article_id / content_key 稳定轮换；默认仅 9 款 base，可扩池到含衍体。"""
    variants = _rotation_pool(brief)
    if not variants:
        variants = list_ai_news_variants()
    if not variants:
        return {
            "id": "ai_news_fallback",
            "label": "资讯默认",
            "visual_style": "warm_gold",
            "title": {"motion_profile": "tiktok_word_pop", "css": [], "background_colors": ["#0f172a"]},
            "content_slots": [],
            "cta": {"motion_profile": "cta_pulse_arrow", "css": []},
            "opening": {"duration_frames": 84, "max_hook_beats": 2},
            "caption": {},
        }
    explicit = str(brief.get("pinned_ai_news_template_id") or "").strip()
    pool_key = str(brief.get("ai_news_rotation_pool") or "fixed").strip().lower()
    if not explicit and pool_key in ("fixed", ""):
        explicit = PINNED_AI_NEWS_PRODUCTION_TEMPLATE_ID
    if explicit:
        for v in list_ai_news_variants():
            if v.get("id") == explicit:
                return dict(v)
    seed = str(
        brief.get("article_id")
        or brief.get("content_key")
        or brief.get("title")
        or "ai_news"
    )
    idx = _seed_int(seed) % len(variants)
    return dict(variants[idx])


def build_ai_news_hook_beats(brief: dict[str, Any], *, tone: str = "") -> list[str]:
    """资讯片头双 beat：悬念 + 新闻点（无 Star）。"""
    title = str(brief.get("title") or "").strip()
    hook = str(brief.get("hook") or "").strip()
    raw = hook or title
    raw = _BANNED_NEWS_COPY.sub("", raw).strip("，,。！？ ")
    t = tone or "breaking"
    _b1 = {
        "breaking": "别划走，先说重点",
        "bulletin": "刚刚，这条值得看",
        "editorial": "很多人忽略了这一点",
        "neon": "你刷到这条不亏",
        "calm": "先安静看完这条",
        "urgent": "注意，这条有变化",
        "analysis": "先把逻辑说清楚",
        "hype": "这事已经传疯了",
        "minimal": "30秒带你看懂",
        "paper": "一图读懂这条",
        "prism": "信息量有点大",
    }
    b1 = (_b1.get(t) or _b1["breaking"])[:18]
    parts = re.split(r"(?<=[。！？?!，,])", raw)
    chunks = [p.strip("，,。！？?! ") for p in parts if 4 <= len(p.strip()) <= 18]
    b2 = chunks[0] if chunks else (title[:18] or "最新进展")
    b2 = _BANNED_NEWS_COPY.sub("", b2).strip()[:18] or b1
    beats = [b1, b2]
    dedup: list[str] = []
    seen: set[str] = set()
    for b in beats:
        if b and b not in seen:
            dedup.append(b)
            seen.add(b)
    return dedup[:DOUYIN_MAX_HOOK_BEATS]


def _content_slides(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in slides if s.get("scene_focus") or str(s.get("type")) == "content_card"]


def apply_pinned_ai_news_plan(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
    template: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """套用钉死资讯款式：片头/内容槽/CTA 动效与装饰。"""
    if not is_news_brief(brief):
        return slides
    tmpl = template or pick_ai_news_template(brief)
    tid = str(tmpl.get("id") or "ai_news_unknown")
    title_cfg = tmpl.get("title") or {}
    cta_cfg = tmpl.get("cta") or {}
    slots = list(tmpl.get("content_slots") or [])
    opening = tmpl.get("opening") or {}
    cap = tmpl.get("caption") or {}
    grad = list(tmpl.get("gradient_colors") or title_cfg.get("background_colors") or ["#0f172a"])
    from python_agent.ai_news_visual import apply_variant_visual_dna

    staged = apply_variant_visual_dna([dict(s) for s in slides], tmpl)
    out: list[dict[str, Any]] = []
    ci = 0
    for s in staged:
        slide = dict(s)
        st = str(slide.get("type") or "")
        for d in list(GITHUB_DECOR):
            slide.pop(d, None)
        slide.pop("repo_name", None)
        slide.pop("repo_url", None)
        slide.pop("star_count", None)
        slide.pop("shot_design", None)
        slide.pop("shot_design_source", None)
        slide["pinned_ai_news_template_id"] = tid

        if st == "title_card":
            slide["motion_profile"] = title_cfg.get("motion_profile") or "tiktok_word_pop"
            slide["css_decorations"] = [
                d for d in (title_cfg.get("css") or []) if d not in GITHUB_DECOR
            ]
            slide["background_color"] = grad[0]
            slide["opening_burst"] = True
            burst = int(opening.get("duration_frames") or DOUYIN_OPENING_BURST_FRAMES)
            slide["opening_duration_frames"] = min(burst, DOUYIN_OPENING_BURST_FRAMES)
            slide["hook_beats"] = build_ai_news_hook_beats(
                brief, tone=str(opening.get("hook_tone") or "")
            )
            slide["caption_mode"] = cap.get("mode") or "tiktok"
            vd = dict(slide.get("visual_design") or {})
            vd["broadcast_frame"] = False
            slide["visual_design"] = vd
        elif st == "cta_card":
            slide["motion_profile"] = cta_cfg.get("motion_profile") or "cta_pulse_arrow"
            slide["css_decorations"] = list(cta_cfg.get("css") or [])
            slide["suppress_bottom_caption"] = True
            slide["mid_info_layout"] = "none"
            slide["viz_type"] = "none"
        elif st == "content_card" or slide.get("scene_focus"):
            slide["type"] = "content_card"
            slot = slots[ci % len(slots)] if slots else {}
            ci += 1
            si = (ci - 1) % max(len(grad), 1)
            slide["background_color"] = grad[si % len(grad)]
            slide["motion_profile"] = slot.get("motion_profile") or "bullet_stagger_up"
            slide["css_decorations"] = [
                d for d in (slot.get("css") or []) if d not in GITHUB_DECOR
            ]
            slide["mid_effect"] = slot.get("mid_effect") or "glow_ring"
            slide["mid_info_layout"] = slot.get("mid_info_layout") or "framed"
            slide["viz_type"] = "none"
            slide["show_chart"] = False
            vd = dict(slide.get("visual_design") or {})
            vd["broadcast_frame"] = False
            slide["visual_design"] = vd
            mp = dict(slide.get("motion_params") or {})
            mp["staggerFrames"] = min(16, max(14, int(mp.get("staggerFrames") or 14)))
            mp["maxCharsPerPage"] = int(cap.get("max_chars_per_page") or 22)
            mp["captionBottomPx"] = int(cap.get("caption_bottom_px") or 320)
            mp["midSafeBottomRatio"] = float(cap.get("mid_safe_bottom_ratio") or 0.4)
            slide["motion_params"] = mp
            slide.pop("opening_duration_frames", None)
        dec = [d for d in (slide.get("css_decorations") or []) if d not in GITHUB_DECOR]
        slide["css_decorations"] = dec
        out.append(slide)
    return out
