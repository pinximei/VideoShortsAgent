"""分平台字幕与中部排版预设（抖音 vs 小红书）。"""
from __future__ import annotations

from typing import Any

DOUYIN = "douyin"
XHS = "xhs"

_PRESETS: dict[str, dict[str, Any]] = {
    DOUYIN: {
        "caption_mode": "tiktok",
        "caption_use_tts_timeline": True,
        "caption_platform": "douyin",
        "motion_params": {
            "wordsPerPageMs": 2400,
            "maxCharsPerPage": 18,
            "captionFontScale": 1.0,
            "captionBottomPx": 320,
        },
        "visual_design": {
            "color_mood": "warm",
            "particle_type": "warm",
            "broadcast_frame": True,
            "text_color": "#fff8f0",
            "accent_color": "#FF9F43",
            "accent_color2": "#FFD93D",
            "caption_style": "spring",
        },
        "background_color": "#120908",
        "mid_hero_max_chars": 16,
        "mid_hero_font_scale": 1.0,
        "caption_word_highlight": True,
    },
    XHS: {
        "caption_mode": "semantic",
        "caption_use_tts_timeline": True,
        "caption_platform": "xhs",
        "motion_params": {
            "wordsPerPageMs": 3600,
            "maxCharsPerPage": 24,
            "captionFontScale": 0.72,
            "captionBottomPx": 200,
        },
        "visual_design": {
            "color_mood": "cool",
            "particle_type": "cool",
            "broadcast_frame": False,
            "text_color": "#e8eef7",
            "accent_color": "#3b82f6",
            "accent_color2": "#22d3ee",
            "caption_style": "fade",
        },
        "background_color": "#151c28",
        "mid_hero_max_chars": 20,
        "mid_hero_font_scale": 0.92,
        "mid_effect_default": "glow_scan",
        "mid_info_layout": "steps",
        "caption_word_highlight": True,
    },
}


def get_platform_preset(platform: str) -> dict[str, Any]:
    pid = (platform or DOUYIN).strip().lower()
    return dict(_PRESETS.get(pid, _PRESETS[DOUYIN]))


def apply_platform_caption_preset(slide: dict[str, Any], platform: str) -> dict[str, Any]:
    """合并平台字幕/画风字段到 slide（不覆盖 LLM 已填的 summary_lines 等）。"""
    s = dict(slide)
    preset = get_platform_preset(platform)
    pid = (platform or "").strip().lower()

    s["caption_mode"] = preset.get("caption_mode", s.get("caption_mode"))
    s["caption_use_tts_timeline"] = preset.get("caption_use_tts_timeline", True)
    s["caption_platform"] = preset.get("caption_platform", pid or DOUYIN)
    s["platform"] = pid or s.get("platform")

    mp = dict(s.get("motion_params") or {})
    for k, v in (preset.get("motion_params") or {}).items():
        mp.setdefault(k, v)
    s["motion_params"] = mp

    s["background_color"] = s.get("background_color") or preset.get("background_color")
    vd = dict(s.get("visual_design") or {})
    for k, v in (preset.get("visual_design") or {}).items():
        vd.setdefault(k, v)
    s["visual_design"] = vd
    s.setdefault("caption_style", vd.get("caption_style"))

    if pid == XHS and not s.get("mid_info_layout"):
        s["mid_info_layout"] = preset.get("mid_info_layout", "steps")
    s["mid_hero_max_chars"] = int(
        s.get("mid_hero_max_chars") or preset.get("mid_hero_max_chars") or 16
    )
    mp["midHeroFontScale"] = float(
        mp.get("midHeroFontScale") or preset.get("mid_hero_font_scale") or 1.0
    )
    s["motion_params"] = mp
    if not s.get("mid_effect") and preset.get("mid_effect_default"):
        s["mid_effect"] = preset["mid_effect_default"]

    return s


def apply_platform_presets_to_slides(
    slides: list[dict[str, Any]], platform: str
) -> list[dict[str, Any]]:
    return [apply_platform_caption_preset(s, platform) for s in slides]
