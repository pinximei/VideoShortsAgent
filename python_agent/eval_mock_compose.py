"""评测用离线分镜（不调用 LLM Compose）。"""
from __future__ import annotations

from typing import Any


def mock_compose_from_brief(brief: dict[str, Any]) -> dict[str, Any]:
    title = str(brief.get("title") or "示例标题")[:28]
    hook = str(brief.get("hook") or "别划走，今天这个真的值得看")[:80]
    points = [str(p).strip() for p in (brief.get("talking_points") or []) if str(p).strip()][:4]
    cta = str(brief.get("cta") or "收藏备用")[:40]

    slides: list[dict[str, Any]] = [
        {
            "type": "title_card",
            "heading": title[:14],
            "hook_text": hook[:18],
            "tts_text": f"{hook}。{title}。",
            "hook_beats": [hook[:18], title[:14]],
        },
    ]
    for i, p in enumerate(points or ["核心亮点", "上手简单"]):
        slides.append(
            {
                "type": "content_card",
                "heading": p[:14],
                "feature_label": f"要点{i + 1}",
                "tts_text": f"{p}。这是第{i + 1}个重点，建议收藏。",
                "bullets": [p[:36]],
                "scene_focus": True,
                "scene_index": i,
            }
        )
    slides.append(
        {
            "type": "cta_card",
            "heading": "行动",
            "cta_text": cta,
            "tts_text": f"{cta}。链接在简介。",
        }
    )
    return {"slides": slides}
