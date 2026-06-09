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

_BANNED_NEWS_COPY = re.compile(
    r"star|⭐|开源|仓库|github",
    re.I,
)


def is_news_brief(brief: dict[str, Any] | None) -> bool:
    if not brief:
        return False
    fk = str(brief.get("feed_kind") or "").strip().lower()
    theme = str(brief.get("theme_id") or "").strip().lower()
    scene = str(brief.get("scene") or brief.get("render_scene") or "").strip().lower()
    return fk == "news" or theme == "ai_news" or scene == "ai_news"


_AI_NEWS_TTS_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("GitHub杀疯了", "这条资讯值得关注"),
    ("github杀疯了", "这条资讯值得关注"),
    ("开源神器", "新产品"),
    ("Star一下", "关注一下"),
    ("star一下", "关注一下"),
    ("点个star", "关注一下"),
    ("点链接", "看评论区"),
    ("链接看", "评论区看"),
)


def product_name_from_brief(brief: dict[str, Any] | None) -> str:
    """从标题提取产品名（如 Bluedot 2.1：… → Bluedot）。"""
    title = str((brief or {}).get("title") or "").strip()
    if not title:
        return ""
    m = re.match(r"^([A-Za-z][\w.\- ]*?)(?:\s*[\d.]+)?\s*[：:]", title)
    if m:
        return m.group(1).strip()
    head = re.split(r"[：:]", title, maxsplit=1)[0].strip()
    return (head.split()[0] if head else "")[:24]


def news_cta_display_text(brief: dict[str, Any] | None) -> str:
    """CTA 屏大字：不用 URL，用关注引导。"""
    from python_agent.platform_traffic_rules import safe_video_cta

    return safe_video_cta(brief)


def enforce_ai_news_product_clarity(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """片头必须点明「是什么产品」，避免观众听不懂。"""
    if not is_news_brief(brief):
        return slides
    pname = product_name_from_brief(brief)
    if not pname:
        return slides
    out: list[dict[str, Any]] = []
    for i, slide in enumerate(slides):
        s = dict(slide)
        if i == 0 and str(s.get("type") or "") == "title_card":
            tts = str(s.get("tts_text") or "").strip()
            if pname.lower() not in tts.lower():
                s["tts_text"] = sanitize_ai_news_tts(
                    f"今天说的产品是 {pname}。{tts}"
                )[:130]
            if pname.lower() not in str(s.get("heading") or "").lower():
                s["heading"] = pname[:14]
            beats = _strip_star_beats(list(s.get("hook_beats") or []))
            if beats and pname.lower() not in beats[0].lower():
                beats[0] = f"{pname}是什么"[:18]
            elif not beats:
                beats = [f"{pname}是什么"[:18], "30秒讲清"]
            s["hook_beats"] = beats[:2]
        out.append(s)
    return out


def enforce_ai_news_cta_slide(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not is_news_brief(brief):
        return slides
    cta_line = news_cta_display_text(brief)
    out: list[dict[str, Any]] = []
    for s in slides:
        slide = dict(s)
        if str(slide.get("type") or "") == "cta_card":
            if not str(slide.get("cta_text") or "").strip():
                slide["cta_text"] = cta_line
            if not str(slide.get("heading") or "").strip():
                slide["heading"] = "关注不迷路"
            if str(slide.get("cta_text") or "").startswith("http"):
                slide["cta_text"] = cta_line
            tts = str(slide.get("tts_text") or "")
            if any(
                x in tts
                for x in ("http", "ai-trends", "点链接", "放链接", "简介了", "放简介", "链接看")
            ):
                slide["tts_text"] = "完整解读看评论区。关注我，每天一条 AI 资讯。"
        out.append(slide)
    return out


def sanitize_ai_news_tts(text: str) -> str:
    """爱资讯口播：去掉 GitHub/Star/开源 语义并补全可读句。"""
    from python_agent.tts_copy_rules import sanitize_tts_text

    s = sanitize_tts_text(text or "")
    s = _BANNED_NEWS_COPY.sub("", s)
    for old, new in _AI_NEWS_TTS_REPLACEMENTS:
        s = s.replace(old, new)
    s = re.sub(r"[，,]{2,}", "，", s)
    s = re.sub(r"\s+", " ", s).strip("，,。！？ ")
    if len(s) < 8:
        return "Bluedot 让每场对话成为 AI 上下文，值得关注。"
    return s


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
    from python_agent.platform_traffic_rules import sanitize_slides_traffic

    slides = sanitize_slides_traffic(slides)
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
            if slide.get("pinned_ai_news_template_id"):
                merged = [d for d in dec if d not in GITHUB_DECOR]
                for d in NEWS_TITLE_CSS:
                    if d == "corner-brackets" and merged:
                        continue
                    if d not in merged:
                        merged.append(d)
                slide["css_decorations"] = merged or list(NEWS_TITLE_CSS)
            else:
                slide["css_decorations"] = list(NEWS_TITLE_CSS)
            beats = _strip_star_beats(list(slide.get("hook_beats") or []))
            if len(beats) < 1:
                hook = str(slide.get("hook_text") or slide.get("heading") or "别划走")[:18]
                beats = [hook]
            slide["hook_beats"] = beats[:2]
            slide.setdefault("motion_profile", "tiktok_word_pop")
        elif st == "cta_card":
            if slide.get("pinned_ai_news_template_id") and dec:
                for d in NEWS_CTA_CSS:
                    if d not in dec:
                        dec.append(d)
                slide["css_decorations"] = dec
            else:
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
