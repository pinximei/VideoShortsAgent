"""Remotion 默认与 caption_style 映射。"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_agent.capabilities.registry import (
    DEFAULT_USE_REMOTION,
    merge_render_effects,
    resolve_caption_style,
)


def test_default_use_remotion_true() -> None:
    assert DEFAULT_USE_REMOTION is True


def test_resolve_caption_style_maps_preset_name() -> None:
    assert resolve_caption_style("情感", default="spring") == "fade"
    assert resolve_caption_style("spring", default="fade") == "spring"


def test_merge_render_effects_defaults_remotion_on() -> None:
    clips = [{"tts_text": "测试", "caption_style": "情感"}]
    fx = merge_render_effects("douyin", clips, {"use_remotion": False})
    assert fx["use_remotion"] is True
    assert clips[0]["caption_style"] == "fade"
