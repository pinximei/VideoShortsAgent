"""平台 G+V 默认配对与口播补齐。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from python_agent.motion_templates import pick_github_daily_style
from python_agent.platform_gv_defaults import PLATFORM_GV
from python_agent.voice_content_templates import (
    expand_script_tts_to_minimum,
    pick_voice_content_style,
    script_tts_char_total,
)


def test_douyin_defaults_v01_g01():
    brief = {"platform": "douyin", "use_platform_gv_default": True, **PLATFORM_GV["douyin"]}
    v = pick_voice_content_style(brief)
    g = pick_github_daily_style(brief)
    assert v.get("id") == "V01_burst_hook_fast"
    assert g.get("id") == "G01_cyber_hook_yellow"


def test_xhs_defaults():
    brief = {"platform": "xhs", "use_platform_gv_default": True, **PLATFORM_GV["xhs"]}
    v = pick_voice_content_style(brief)
    g = pick_github_daily_style(brief)
    assert v.get("id") == "V04_minimal_calm"
    assert g.get("id") == "G03_minimal_white_series"


def test_expand_script_tts():
    style = {"total_chars": [180, 260]}
    script = {
        "slides": [
            {"type": "title_card", "tts_text": "别划走，今天这个项目很猛。"},
            {"type": "content_card", "tts_text": "它能自动抓趋势。"},
            {"type": "cta_card", "tts_text": "链接在评论区。"},
        ]
    }
    before = script_tts_char_total(script["slides"])
    out = expand_script_tts_to_minimum(script, style)
    after = script_tts_char_total(out["slides"])
    assert after > before
    assert after >= 160
