"""clip bullets 解析与 apps  enrich。"""
from __future__ import annotations

from python_agent.capabilities.clip_text import (
    bullets_from_prose,
    clip_bullets,
    enrich_apps_platform_copy,
)


def test_bullets_from_prose_chinese_separators() -> None:
    text = "\u7701\u65f6\u95f4\u00b7\u6613\u4e0a\u624b\u00b7\u53ef\u5546\u7528"
    out = bullets_from_prose(text)
    assert len(out) == 3


def test_enrich_apps_adds_bullets() -> None:
    copy = {
        "douyin": {
            "title": "t",
            "effects": {"preset": "科技"},
            "clips": [
                {"start": 0, "end": 8, "hook_text": "开场", "tts_text": "开场口播", "transition_to_next": "fade"},
                {
                    "start": 10,
                    "end": 20,
                    "hook_text": "\u8ba2\u9605\u53d8\u73b0\u00b7\u5f00\u6e90\u534f\u8bae\u00b7\u4f01\u4e1a\u90e8\u7f72",
                    "tts_text": "第二段口播内容足够长",
                    "transition_to_next": "fade",
                },
                {"start": 22, "end": 30, "hook_text": "结尾", "tts_text": "结尾口播", "transition_to_next": "fade"},
            ],
        }
    }
    out = enrich_apps_platform_copy(copy, feed_kind="apps")
    mid = out["douyin"]["clips"][1]
    assert clip_bullets(mid)


def test_enrich_skips_news() -> None:
    copy = {"douyin": {"clips": [], "effects": {"preset": "严肃"}}}
    assert enrich_apps_platform_copy(copy, feed_kind="news") == copy
