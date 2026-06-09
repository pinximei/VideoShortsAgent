"""爱资讯配图：文章封面 + 免费图库关键词（Pixabay / DuckDuckGo）。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.pipeline_media import prefetch_task_cover, resolve_cover_for_task


def _english_keywords(text: str, *, extra: str = "") -> str:
    """图库搜索用短英文词（2–5 词）。"""
    t = (text or "").strip()
    t = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", t)
    if re.search(r"copilot|windows|microsoft", t, re.I):
        base = "windows laptop office technology"
    elif re.search(r"ai|人工智能|大模型", t, re.I):
        base = "artificial intelligence technology news"
    elif re.search(r"手机|apple|iphone", t, re.I):
        base = "smartphone technology news"
    else:
        base = "technology news digital screen"
    if extra:
        return f"{base} {extra}".strip()[:80]
    return base[:80]


def enrich_news_slide_images(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
    task_dir: Any,
) -> list[dict[str, Any]]:
    """
    为资讯镜补充 needs_image + image_keywords，并尽量挂上文章封面。

    依赖 ImageResolverSkill（config: PIXABAY_API_KEY 或 DuckDuckGo 降级）。
    """
    from pathlib import Path

    task_dir = Path(task_dir)
    cover = prefetch_task_cover(task_dir, brief) or resolve_cover_for_task(
        task_dir, str(brief.get("cover_image_url") or "")
    )
    title_kw = _english_keywords(str(brief.get("title") or ""))
    out: list[dict[str, Any]] = []
    content_i = 0
    for s in slides:
        slide = dict(s)
        st = str(slide.get("type") or "")
        if st == "title_card":
            slide["needs_image"] = True
            slide["image_keywords"] = title_kw
            if cover:
                slide["image_path"] = str(cover.resolve())
                slide["image"] = cover.name
        elif st == "content_card" or slide.get("scene_focus"):
            slide["needs_image"] = True
            hero = str(slide.get("feature_label") or slide.get("heading") or "")[:40]
            slide["image_keywords"] = _english_keywords(hero or title_kw, extra="abstract")
            if content_i == 0 and cover and not slide.get("image_path"):
                slide["image_path"] = str(cover.resolve())
            content_i += 1
        out.append(slide)
    return out
