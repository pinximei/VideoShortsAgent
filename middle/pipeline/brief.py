from __future__ import annotations

import re
from typing import Any

from .models import VideoBrief, content_key_for_article
from .article_content import (
    MIN_TALKING_POINT_CHARS,
    collect_article_text,
    extract_talking_point_candidates,
    is_placeholder_summary,
    plain_without_urls,
)

# 与 VSA python_agent.pipeline_quality 对齐的口播可渲染判断
MIN_BRIEF_RENDER_CHARS = 40


def brief_is_renderable(brief: VideoBrief | dict[str, Any]) -> tuple[bool, str]:
    data = brief.to_dict() if hasattr(brief, "to_dict") else dict(brief)
    parts = [
        data.get("hook") or "",
        *(data.get("talking_points") or []),
        data.get("cta") or "",
    ]
    plain = plain_without_urls(" ".join(str(p) for p in parts if p))
    if len(plain) < MIN_BRIEF_RENDER_CHARS:
        return False, f"口播实质字数 {len(plain)} < {MIN_BRIEF_RENDER_CHARS}，跳过渲染"
    if len(plain_without_urls(str(data.get("hook") or ""))) < 4:
        return False, "钩子过短"
    return True, ""


def _plain(text: str, *, max_len: int = 400) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    s = re.sub(r"[#*_`>\[\]]+", "", s)
    return s[:max_len]


def _worth_score(article: dict[str, Any]) -> int | None:
    repl = article.get("replication_analysis") or {}
    raw = repl.get("worth_score")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _tab_summary(article: dict[str, Any], label: str) -> str:
    for tab in article.get("tabs") or []:
        if not isinstance(tab, dict):
            continue
        if (tab.get("label") or "").strip() == label:
            return _plain(str(tab.get("summary") or ""), max_len=280)
    for tab in article.get("tab_summaries") or []:
        if not isinstance(tab, dict):
            continue
        if (tab.get("label") or "").strip() == label:
            return _plain(str(tab.get("summary") or ""), max_len=280)
    return ""


def build_brief(article: dict[str, Any], *, public_base_url: str, theme_id: str = "") -> VideoBrief:
    article_id = int(article["id"])
    title = _plain(str(article.get("title") or ""), max_len=120)
    slug = (article.get("slug") or "").strip()
    detail_url = f"{public_base_url.rstrip('/')}/resource/{slug}" if slug else public_base_url

    repl = article.get("replication_analysis") or {}
    from python_agent.capabilities.opening_hook import scroll_stopping_hook

    raw_hook = _plain(
        str(repl.get("value_summary") or article.get("card_value_hook") or title),
        max_len=80,
    )
    hook = scroll_stopping_hook(
        title=title,
        hook=raw_hook,
        feed_kind=str(article.get("feed_kind") or "news"),
    )

    points = extract_talking_point_candidates(article, max_points=3)
    article_body_plain = plain_without_urls((article.get("article_body") or "").strip())
    if len(article_body_plain) >= 80 and len(points) < 3:
        for chunk in re.split(r"[。！？\n]+", article_body_plain):
            plain = plain_without_urls(chunk)
            if len(plain) >= MIN_TALKING_POINT_CHARS and plain not in points:
                points.append(plain[:280])
            if len(points) >= 3:
                break
    if len(points) < 2:
        for label in ("描述", "变现评估", "数据支撑"):
            t = _tab_summary(article, label)
            if t and len(plain_without_urls(t)) >= 12 and t not in points:
                points.append(t)
    if len(points) < 2:
        summary = _plain(str(article.get("summary") or article.get("card_description") or ""), max_len=400)
        if summary and not is_placeholder_summary(summary) and summary not in points:
            points.append(summary)
    if len(points) < 1:
        excerpt = plain_without_urls(collect_article_text(article, max_chars=2000))
        if len(excerpt) >= 40:
            points.append(excerpt[:280])
    points = points[:3]

    mp = repl.get("market_position") or {}
    hypo = _plain(str(mp.get("monetization_hypothesis") or ""), max_len=120)
    if hypo and len(points) < 3:
        points.append(hypo)
    points = points[:3]

    cta = f"完整变现拆解见 {detail_url}"
    cats = article.get("categories") or []
    tags = [str(c) for c in cats[:4] if c]
    if not tags:
        tags = ["AI工具", "独立开发"]

    return VideoBrief(
        content_key=content_key_for_article(article_id),
        article_id=article_id,
        title=title,
        hook=hook or title,
        talking_points=points,
        cta=cta,
        tags=tags,
        worth_score=_worth_score(article),
        feed_kind=str(
            article.get("feed_kind")
            or ("news" if (theme_id or "").strip().lower() == "ai_news" else "apps")
        ),
        source_key=str(article.get("admin_source_key") or ""),
        theme_id=theme_id,
        detail_url=detail_url,
        source_url=str(article.get("source_original_url") or ""),
        cover_image_url=str(article.get("cover_image_url") or "")[:2048],
    )


def passes_filter(article: dict[str, Any], *, min_worth: int, feed_kinds: list[str]) -> tuple[bool, str]:
    fk = str(article.get("feed_kind") or "")
    if feed_kinds and fk not in feed_kinds:
        return False, f"feed_kind={fk} not in {feed_kinds}"
    worth = _worth_score(article)
    if worth is None:
        if article.get("value_assessed") is False and article.get("high_value_pick") is False:
            return False, "no worth_score"
        worth = 7 if article.get("value_assessed") else 0
    if worth < min_worth:
        return False, f"worth_score {worth} < {min_worth}"
    return True, ""
