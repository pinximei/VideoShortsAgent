"""TTS 参数与 V/G 分离逻辑。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from python_agent.tts_params import resolve_tts_params  # noqa: E402


def test_asr_style_uses_measured_rate():
    t = resolve_tts_params(
        {"words_per_minute": 369, "edge_tts_rate": "+18%", "validation_note": "dashscope_paraformer_v2"},
        platform_voice="zh-CN-YunxiNeural",
    )
    assert t["tts_rate"] == "+18%"
    assert t["tts_voice"] == "zh-CN-YunyangNeural"


def test_phash_only_not_slow_five_percent():
    t = resolve_tts_params(
        {
            "validation_note": "phash_bottom_band",
            "phash_only": True,
            "subtitle_switch_ms": 500,
            "edge_tts_rate": "+5%",
        },
        platform_voice="zh-CN-YunxiNeural",
    )
    assert t["tts_rate"] in ("+14%", "+16%")
    assert t["tts_pitch"] == "+10Hz"


def test_slow_subtitle_gets_lower_pitch():
    t = resolve_tts_params(
        {"subtitle_switch_ms": 4000, "validation_note": "phash_bottom_band", "phash_only": True},
        platform_voice="zh-CN-YunxiNeural",
    )
    assert t["tts_rate"] == "+8%"
    assert t["tts_pitch"] == "+0Hz"
