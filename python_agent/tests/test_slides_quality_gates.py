"""slides_quality_gates 单元测试。"""
from __future__ import annotations

from python_agent.slides_quality_gates import (
    auto_fix_slides,
    summarize_quality_gate,
    validate_slides_before_render,
)


def test_auto_fix_empty_summary():
    slides = [
        {
            "type": "content_card",
            "scene_focus": True,
            "heading": "测试项目",
            "tts_text": "这是一段口播",
            "viz_type": "line",
            "chart_series": [1],
        }
    ]
    fixed = auto_fix_slides(slides, platform="douyin")
    assert fixed[0]["viz_type"] == "none"
    assert fixed[0].get("summary_lines")


def test_validate_gate_ok():
    slides = [
        {
            "type": "title_card",
            "tts_text": "别划走",
            "hook_beats": ["别划走", "真的炸裂"],
        },
        {
            "type": "content_card",
            "scene_focus": True,
            "summary_lines": ["亮点一", "亮点二"],
            "tts_text": "完整口播句子",
            "viz_type": "none",
        },
    ]
    gate = validate_slides_before_render(slides, platform="douyin")
    assert gate["ok"] is True


def test_title_card_hook_cap():
    slides = [{"type": "title_card", "hook_beats": ["a", "b", "c", "d"], "opening_duration_frames": 200}]
    fixed = auto_fix_slides(slides, platform="douyin")
    assert len(fixed[0]["hook_beats"]) <= 2
    assert fixed[0]["opening_duration_frames"] <= 84


def test_summarize_quality_gate():
    text = summarize_quality_gate({"ok": False, "errors": ["e1"], "warnings": ["w1"], "platform": "douyin", "slide_count": 3})
    assert "未通过" in text
    assert "e1" in text
