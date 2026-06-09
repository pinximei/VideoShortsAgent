"""爱资讯成片默认：黑金模板 + 晓晓播报（与 middle/config.yaml 同步）。"""
from __future__ import annotations

from typing import Any

from python_agent.pinned_ai_news_template import (
    PINNED_AI_NEWS_PRODUCTION_TEMPLATE_ID,
)
from python_agent.tts_voice_presets import DEFAULT_NEWS_PRESET_ID


def apply_ai_news_production_defaults(
    brief: dict[str, Any],
    *,
    template_id: str = "",
    tts_voice_preset: str = "",
) -> dict[str, Any]:
    """写入固定模板/口播预设，避免按文章 id 轮换其它配色款。"""
    fk = str(brief.get("feed_kind") or "").strip().lower()
    theme = str(brief.get("theme_id") or "").strip().lower()
    if fk != "news" and theme != "ai_news":
        return brief
    out = dict(brief)
    out["pinned_ai_news_template_id"] = (
        (template_id or "").strip() or PINNED_AI_NEWS_PRODUCTION_TEMPLATE_ID
    )
    out["tts_voice_preset"] = (tts_voice_preset or "").strip() or DEFAULT_NEWS_PRESET_ID
    out.setdefault("ai_news_rotation_pool", "fixed")
    return out
