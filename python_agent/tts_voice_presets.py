"""口播音色预设：爱资讯等讲解类成片用固定播报腔，避免 V 模板 / 平台默认把语速拉乱。"""
from __future__ import annotations

import os
from typing import Any

# Microsoft Edge 中文神经语音（常用讲解 / 播报；完整列表见 edge-tts --list-voices）
EDGE_ZH_VOICES_DOC = """
zh-CN-XiaoxiaoNeural  女声·亲切温暖（推荐资讯播报）
zh-CN-XiaoyiNeural    女声·活泼
zh-CN-XiaohanNeural   女声·平静
zh-CN-YunjianNeural   男声·纪录片 / 新闻解说
zh-CN-YunxiNeural     男声·沉稳（偏广告）
zh-CN-YunyangNeural   男声·新闻快讯（偏快）
zh-CN-YunzeNeural     男声·低沉
""".strip()

VOICE_PRESETS: dict[str, dict[str, Any]] = {
    "news_anchor_female": {
        "id": "news_anchor_female",
        "label": "女声·亲切播报（晓晓）",
        "tts_voice": "zh-CN-XiaoxiaoNeural",
        "edge_tts_rate": "+0%",
        "edge_tts_pitch": "+0Hz",
        "sentence_pause_sec": 0.38,
        "words_per_minute": 190,
        "tone": "亲切、平稳，像资讯主播讲解产品；不急不躁，不要喊麦、广告腔或短视频爆款语速",
        "hook_pattern": "今天说的产品是|先说是什么|很多人还没听过",
        "total_chars": [155, 195],
        "slide_chars": {
            "title_card": [26, 42],
            "content_card": [38, 58],
            "cta_card": [16, 28],
        },
    },
    "news_anchor_male": {
        "id": "news_anchor_male",
        "label": "男声·新闻解说（云健）",
        "tts_voice": "zh-CN-YunjianNeural",
        "edge_tts_rate": "+4%",
        "edge_tts_pitch": "+1Hz",
        "sentence_pause_sec": 0.32,
        "words_per_minute": 220,
    },
    "news_anchor_tv": {
        "id": "news_anchor_tv",
        "label": "男声·电视快讯（云扬）",
        "tts_voice": "zh-CN-YunyangNeural",
        "edge_tts_rate": "+10%",
        "edge_tts_pitch": "+3Hz",
        "sentence_pause_sec": 0.22,
        "words_per_minute": 280,
    },
    "vibecoding_understated_rank": {
        "id": "vibecoding_understated_rank",
        "label": "不露声色·VibeCoding榜单解说（云健）",
        "tts_voice": "zh-CN-YunjianNeural",
        "edge_tts_rate": "+11%",
        "edge_tts_pitch": "+5Hz",
        "sentence_pause_sec": 0.30,
        "words_per_minute": 248,
    },
}

DEFAULT_NEWS_PRESET_ID = "news_anchor_female"


def resolve_voice_preset_id(brief: dict[str, Any] | None = None) -> str:
    b = brief or {}
    explicit = str(b.get("tts_voice_preset") or "").strip()
    if explicit and explicit in VOICE_PRESETS:
        return explicit
    env = (os.getenv("TTS_VOICE_PRESET") or "").strip()
    if env and env in VOICE_PRESETS:
        return env
    return DEFAULT_NEWS_PRESET_ID


def load_voice_preset(preset_id: str | None = None, *, brief: dict[str, Any] | None = None) -> dict[str, Any]:
    pid = preset_id or resolve_voice_preset_id(brief)
    base = dict(VOICE_PRESETS.get(pid) or VOICE_PRESETS[DEFAULT_NEWS_PRESET_ID])
    base["id"] = pid
    return base


def list_voice_presets() -> list[dict[str, str]]:
    return [{"id": k, "label": str(v.get("label") or k)} for k, v in VOICE_PRESETS.items()]


def compose_voice_style_from_preset(brief: dict[str, Any] | None = None) -> dict[str, Any]:
    """爱资讯 Compose 用：与成片 TTS 预设一致，避免 V20 快节奏绑死文案。"""
    preset = load_voice_preset(brief=brief)
    return {
        "id": preset.get("id") or DEFAULT_NEWS_PRESET_ID,
        "name": preset.get("label") or "资讯播报",
        "tone": preset.get("tone") or "亲切平稳的资讯讲解",
        "hook_pattern": preset.get("hook_pattern") or "今天说的产品是",
        "words_per_minute": int(preset.get("words_per_minute") or 190),
        "total_chars": list(preset.get("total_chars") or [155, 195]),
        "slide_chars": dict(preset.get("slide_chars") or {}),
        "tts_voice": preset.get("tts_voice"),
        "edge_tts_rate": preset.get("edge_tts_rate"),
        "edge_tts_pitch": preset.get("edge_tts_pitch"),
        "sentence_pause_sec": preset.get("sentence_pause_sec"),
    }
