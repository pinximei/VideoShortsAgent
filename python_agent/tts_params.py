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

# 平台默认（未命中 V 模板时）：抖音男声易偏慢，用 Yunyang + 更快 rate；小红书女声保持 Xiaoxiao
PLATFORM_TTS_DEFAULTS: dict[str, dict[str, Any]] = {
    "douyin": {
        "tts_voice": "zh-CN-YunyangNeural",
        "tts_rate": "+14%",
        "tts_pitch": "+8Hz",
        "sentence_pause_sec": 0.14,
    },
    "xhs": {
        "tts_voice": "zh-CN-XiaoxiaoNeural",
        "tts_rate": "+6%",
        "tts_pitch": "+4Hz",
        "sentence_pause_sec": 0.18,
    },
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


def resolve_tts_for_platform(
    brief: dict[str, Any],
    platform_id: str,
    *,
    voice_style: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """成片 TTS：优先 brief/V 模板，否则平台默认（修复抖音男声 Yunxi+0% 过慢）。"""
    from python_agent.platform_presets import get_platform_preset

    preset = get_platform_preset(platform_id)
    style = dict(voice_style or brief.get("voice_content_style") or {})
    if not style and brief.get("voice_content_style_id"):
        try:
            from python_agent.voice_content_templates import load_voice_catalog

            for s in load_voice_catalog().get("styles") or []:
                if s.get("id") == brief.get("voice_content_style_id"):
                    style = dict(s)
                    break
        except Exception:
            pass
    if style:
        return resolve_tts_params(style, platform_voice=preset.voice)
    plat = PLATFORM_TTS_DEFAULTS.get(platform_id, PLATFORM_TTS_DEFAULTS["douyin"])
    return {
        "tts_voice": plat.get("tts_voice") or preset.voice,
        "tts_rate": plat.get("tts_rate", "+12%"),
        "tts_pitch": plat.get("tts_pitch", "+0Hz"),
        "sentence_pause_sec": float(plat.get("sentence_pause_sec", 0.16)),
    }


def load_tts_from_task_dir(task_dir: str | Path) -> dict[str, Any]:
    """读取 task 已保存的 brief + voice_content_style。"""
    root = Path(task_dir)
    out: dict[str, Any] = {}
    for name in ("brief.json", "llm/brief.json"):
        p = root / name
        if p.is_file():
            import json

            out.update(json.loads(p.read_text(encoding="utf-8")))
            break
    vp = root / "llm" / "voice_content_style.json"
    if vp.is_file():
        import json

        data = json.loads(vp.read_text(encoding="utf-8"))
        if isinstance(data.get("style"), dict):
            out["voice_content_style"] = data["style"]
    return out


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
