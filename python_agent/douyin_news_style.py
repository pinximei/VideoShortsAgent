"""爱资讯（feed_kind=news）抖音视觉：去掉 GitHub 仓库语义与装饰。"""
from __future__ import annotations

import re
from typing import Any

GITHUB_DECOR = frozenset(
    {
        "github-badge",
        "odometer-stars",
        "daily-video-tag",
        "rank-number",
        "repo-header",
        "grid-tunnel-bg",
    }
)

NEWS_TITLE_CSS = ["text-stroke-yellow", "sparkle-dots", "corner-brackets", "caption-bottom-safe"]
NEWS_CTA_CSS = ["soft-purple-gradient", "pulse-button", "sparkle-dots", "caption-bottom-safe"]


def is_news_brief(brief: dict[str, Any] | None) -> bool:
    if not brief:
        return False
    fk = str(brief.get("feed_kind") or "").strip().lower()
    theme = str(brief.get("theme_id") or "").strip().lower()
    scene = str(brief.get("scene") or brief.get("render_scene") or "").strip().lower()
    return fk == "news" or theme == "ai_news" or scene == "ai_news"


def _strip_star_beats(beats: list[Any]) -> list[str]:
    out: list[str] = []
    for x in beats:
        t = str(x).strip()[:18]
        if not t:
            continue
        if re.search(r"star|⭐|开源|仓库|github", t, re.I):
            continue
        out.append(t)
    return out


def apply_douyin_news_style(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """从分镜中剥离 GitHub 装饰/字段，统一资讯片头片尾 CSS。"""
    if not is_news_brief(brief):
        return slides
    out: list[dict[str, Any]] = []
    for s in slides:
        slide = dict(s)
        if slide.get("scene_focus") or str(slide.get("type")) == "content_card":
            slide["type"] = "content_card"
            slide.pop("title_card", None)
            slide.pop("repo_name", None)
            slide.pop("repo_url", None)
            slide.pop("star_count", None)
            shot = slide.get("shot_design")
            if isinstance(shot, dict):
                shot = dict(shot)
                shot.pop("stat_value", None)
                shot["viz_type"] = "none" if shot.get("viz_type") == "stat" else shot.get("viz_type")
                slide["shot_design"] = shot
            if str(slide.get("viz_type") or "") == "stat" and not str(brief.get("stars") or ""):
                slide["viz_type"] = "none"
                slide["stat_value"] = ""
        unit = str(slide.get("unit") or "").strip()
        if unit and not str(slide.get("type") or "").strip():
            slide["type"] = unit
        st = str(slide.get("type") or "")
        dec = [d for d in (slide.get("css_decorations") or []) if d not in GITHUB_DECOR]
        if st == "title_card":
            slide["css_decorations"] = list(NEWS_TITLE_CSS)
            beats = _strip_star_beats(list(slide.get("hook_beats") or []))
            if len(beats) < 1:
                hook = str(slide.get("hook_text") or slide.get("heading") or "别划走")[:18]
                beats = [hook]
            slide["hook_beats"] = beats[:2]
            slide.setdefault("motion_profile", "tiktok_word_pop")
        elif st == "cta_card":
            slide["css_decorations"] = list(NEWS_CTA_CSS)
        else:
            slide["css_decorations"] = dec
        vd = dict(slide.get("visual_design") or {})
        vd["css_decorations"] = [
            d for d in (vd.get("css_decorations") or []) if d not in GITHUB_DECOR
        ]
        vd.pop("broadcast_frame", None) if st == "content_card" else None
        slide["visual_design"] = vd
        out.append(slide)
    return out
