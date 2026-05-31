"""
口播 TTS 参数解析：音色 / 语速 / 音调 / 句停顿。

与 motion_templates（画面 Gxx）分离；由 voice_content_templates 选型后在此合并平台默认值。
"""
from __future__ import annotations

from typing import Any

# 对标 B 站 ASR 中位 ~369 字/分；同文案 Edge +0% 实测 ~387 字/分（见 ours_tts_proof.json）
GITHUB_DAILY_TTS_BASELINE: dict[str, Any] = {
    "tts_voice": "zh-CN-YunyangNeural",
    "edge_tts_rate": "+12%",
    "edge_tts_pitch": "+6Hz",
    "sentence_pause_sec": 0.16,
}

FAST_SUBTITLE_MS = 900
SLOW_SUBTITLE_MS = 2500


def rate_from_measured_wpm(wpm: int | None) -> str:
    if wpm is None:
        return str(GITHUB_DAILY_TTS_BASELINE["edge_tts_rate"])
    if wpm >= 380:
        return "+18%"
    if wpm >= 340:
        return "+14%"
    if wpm >= 300:
        return "+12%"
    if wpm >= 260:
        return "+8%"
    return "+5%"


def pitch_from_subtitle_ms(ms: int | None) -> str:
    if ms is None:
        return str(GITHUB_DAILY_TTS_BASELINE["edge_tts_pitch"])
    if ms <= FAST_SUBTITLE_MS:
        return "+10Hz"
    if ms >= SLOW_SUBTITLE_MS:
        return "+0Hz"
    return "+6Hz"


def pause_from_subtitle_ms(ms: int | None) -> float:
    if ms is None:
        return float(GITHUB_DAILY_TTS_BASELINE["sentence_pause_sec"])
    if ms <= FAST_SUBTITLE_MS:
        return 0.12
    if ms >= SLOW_SUBTITLE_MS:
        return 0.24
    return 0.16


def resolve_tts_params(
    voice_style: dict[str, Any],
    *,
    platform_voice: str,
) -> dict[str, Any]:
    """合并 V 模板、实测回填与平台默认；phash-only 不用低 rate。"""
    style = dict(voice_style or {})
    base = GITHUB_DAILY_TTS_BASELINE

    wpm = style.get("words_per_minute")
    phash_only = style.get("phash_only") or style.get("validation_note") == "phash_bottom_band"
    sub_ms = style.get("subtitle_switch_ms")

    voice = (style.get("tts_voice") or "").strip() or str(base["tts_voice"]) or platform_voice

    if wpm and not phash_only:
        rate = style.get("edge_tts_rate") or rate_from_measured_wpm(int(wpm))
    elif phash_only:
        rate = rate_from_subtitle_ms(int(sub_ms)) if sub_ms else str(base["edge_tts_rate"])
    else:
        rate = style.get("edge_tts_rate") or str(base["edge_tts_rate"])

    pitch = style.get("edge_tts_pitch") or pitch_from_subtitle_ms(int(sub_ms) if sub_ms else None)
    pause = style.get("sentence_pause_sec")
    if pause is None:
        pause = pause_from_subtitle_ms(int(sub_ms) if sub_ms else None)

    return {
        "tts_voice": voice,
        "tts_rate": str(rate),
        "tts_pitch": str(pitch),
        "sentence_pause_sec": float(pause),
    }


def rate_from_subtitle_ms(ms: int) -> str:
    if ms <= 600:
        return "+16%"
    if ms <= FAST_SUBTITLE_MS:
        return "+14%"
    if ms >= SLOW_SUBTITLE_MS:
        return "+8%"
    return "+12%"
