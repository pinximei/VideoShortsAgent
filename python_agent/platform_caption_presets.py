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
            "wordsPerPageMs": 2600,
            "maxCharsPerPage": 24,
            "captionFontScale": 0.92,
            "captionBottomPx": 300,
            "captionLetterSpacing": 0,
            "captionLineHeight": 1.06,
            "midSafeBottomRatio": 0.4,
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
        "mid_hero_font_scale": 0.92,
        "opening_duration_frames": 165,
        "caption_word_highlight": True,
    },
    XHS: {
        "caption_mode": "editorial",
        "caption_use_tts_timeline": True,
        "caption_platform": "xhs",
        "motion_params": {
            "wordsPerPageMs": 3000,
            "maxCharsPerPage": 12,
            "captionFontScale": 0.72,
            "captionBottomPx": 440,
            "captionLetterSpacing": 2,
            "captionLineHeight": 1.42,
            "midSafeBottomRatio": 0.52,
            "midSafeTopRatio": 0.1,
        },
        "visual_design": {
            "color_mood": "xhs-soft",
            "particle_type": "warm",
            "broadcast_frame": False,
            "text_color": "#1a1520",
            "accent_color": "#FF6B8A",
            "accent_color2": "#FFB347",
            "caption_style": "fade",
        },
        "background_color": "#f5f5f0",
        "mid_hero_max_chars": 14,
        "mid_hero_font_scale": 0.82,
        "opening_duration_frames": 120,
        "mid_effect_default": "bracket_slam",
        "mid_info_layout": "keywords",
        "caption_word_highlight": False,
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
    st = str(s.get("type") or "")

    s["caption_mode"] = preset.get("caption_mode", s.get("caption_mode"))
    s["caption_use_tts_timeline"] = preset.get("caption_use_tts_timeline", True)
    s["caption_platform"] = preset.get("caption_platform", pid or DOUYIN)
    s["platform"] = pid or s.get("platform")

    mp = dict(s.get("motion_params") or {})
    preset_mp = preset.get("motion_params") or {}
    _force_mp = (
        "wordsPerPageMs",
        "maxCharsPerPage",
        "captionFontScale",
        "captionBottomPx",
        "captionLetterSpacing",
        "captionLineHeight",
        "midSafeBottomRatio",
        "midSafeTopRatio",
    )
    for k, v in preset_mp.items():
        if k in _force_mp or k not in mp:
            mp[k] = v

    if st == "content_card" and pid == DOUYIN:
        layout = str(s.get("mid_info_layout") or "").lower()
        if layout in ("compare", "steps"):
            mp["captionBottomPx"] = max(int(mp.get("captionBottomPx") or 300), 360)
    if st == "cta_card":
        mp["captionBottomPx"] = max(int(mp.get("captionBottomPx") or 300), 380)
        if pid == XHS:
            s["suppress_bottom_caption"] = True
        else:
            s.pop("suppress_bottom_caption", None)

    s["motion_params"] = mp

    if preset.get("background_color"):
        s["background_color"] = preset["background_color"]
    vd = dict(s.get("visual_design") or {})
    preset_vd = preset.get("visual_design") or {}
    _force_vd = (
        "color_mood",
        "particle_type",
        "text_color",
        "accent_color",
        "accent_color2",
        "caption_style",
    )
    for k, v in preset_vd.items():
        if k in _force_vd or k not in vd:
            vd[k] = v
    if st == "title_card":
        vd["broadcast_frame"] = True
    elif pid == XHS:
        vd["broadcast_frame"] = False
    else:
        # 内容镜禁用播报横线，避免与字幕区、卡片边框叠成「满屏线」
        vd["broadcast_frame"] = st == "title_card"
    s["visual_design"] = vd
    s.setdefault("caption_style", vd.get("caption_style"))

    if pid == XHS and st == "content_card" and not s.get("mid_info_layout"):
        s["mid_info_layout"] = preset.get("mid_info_layout", "keywords")
    s["mid_hero_max_chars"] = int(
        s.get("mid_hero_max_chars") or preset.get("mid_hero_max_chars") or 16
    )
    mp["midHeroFontScale"] = float(
        mp.get("midHeroFontScale") or preset.get("mid_hero_font_scale") or 1.0
    )
    s["motion_params"] = mp
    if not s.get("mid_effect") and preset.get("mid_effect_default"):
        s["mid_effect"] = preset["mid_effect_default"]
    if preset.get("opening_duration_frames"):
        s.setdefault("opening_duration_frames", int(preset["opening_duration_frames"]))

    return s


def apply_platform_presets_to_slides(
    slides: list[dict[str, Any]], platform: str
) -> list[dict[str, Any]]:
    out = [apply_platform_caption_preset(s, platform) for s in slides]
    return reconcile_platform_slides(out, platform)


def reconcile_platform_slides(
    slides: list[dict[str, Any]], platform: str
) -> list[dict[str, Any]]:
    """G 模板覆盖后，拉回分平台动效档案与版式。"""
    pid = (platform or "").strip().lower()

    if pid == DOUYIN:
        from python_agent.douyin_layout_registry import CTA_LAYOUT, TITLE_LAYOUT, css_pack
        from python_agent.douyin_layout_registry import layout_for_content_index

        ci = 0
        for s in slides:
            st = str(s.get("type") or "")
            if st == "title_card":
                dec = list(s.get("css_decorations") or [])
                for d in TITLE_LAYOUT["css"]:
                    if d not in dec:
                        dec.append(d)
                if "daily-video-tag" not in dec:
                    dec.append("daily-video-tag")
                s["css_decorations"] = css_pack(dec)
                continue
            if st == "cta_card":
                s["css_decorations"] = list(CTA_LAYOUT["css"])
                s["motion_profile"] = CTA_LAYOUT["motion_profile"]
                continue
            if st != "content_card" and not s.get("scene_focus"):
                continue
            pack = layout_for_content_index(ci)
            ci += 1
            s["motion_profile"] = pack["motion_profile"]
            s["css_decorations"] = list(pack["css"])
            s.setdefault("mid_effect", pack.get("mid_effect") or "typewriter")
            layouts_rot = ("steps", "framed", "keywords")
            if not s.get("shot_design_source"):
                s["mid_info_layout"] = layouts_rot[ci % len(layouts_rot)]
            mp = dict(s.get("motion_params") or {})
            mp["staggerFrames"] = max(18, int(pack.get("stagger_frames") or 18))
            s["motion_params"] = mp
            vd = dict(s.get("visual_design") or {})
            vd["broadcast_frame"] = False
            s["visual_design"] = vd
        return slides

    if pid != XHS:
        return slides

    content_profiles = (
        "tiktok_phrase_pages",
        "kinetic_slam_tight",
        "glass_card_stack",
        "shake_emphasis",
    )
    ci = 0
    for s in slides:
        st = str(s.get("type") or "")
        if st not in ("content_card",) and not s.get("scene_focus"):
            continue

        prof = content_profiles[ci % len(content_profiles)]
        ci += 1
        s["motion_profile"] = prof
        s["background_color"] = "#f5f5f0"
        s["mid_info_layout"] = "keywords" if prof in ("tiktok_phrase_pages", "kinetic_slam_tight") else s.get(
            "mid_info_layout", "keywords"
        )
        s.setdefault("mid_effect", "bracket_slam")

        lines = [str(x).strip()[:10] for x in (s.get("summary_lines") or []) if str(x).strip()]
        if not lines:
            head = str(s.get("heading") or s.get("feature_label") or "核心亮点")
            lines = [head[:10], "收藏备用"]
        s["summary_lines"] = lines[:2]
        kin = [str(x).strip()[:8] for x in (s.get("kinetic_phrases") or []) if str(x).strip()]
        s["kinetic_phrases"] = kin[:3]

        dec = [d for d in (s.get("css_decorations") or []) if d not in ("plain-white-bg", "daily-video-tag")]
        if not dec:
            dec = ["pill-badge", "stat-pill-row"]
        s["css_decorations"] = dec

        vd = dict(s.get("visual_design") or {})
        preset_vd = get_platform_preset(XHS).get("visual_design") or {}
        for k in (
            "color_mood",
            "particle_type",
            "text_color",
            "accent_color",
            "accent_color2",
            "caption_style",
        ):
            if k in preset_vd:
                vd[k] = preset_vd[k]
        vd["broadcast_frame"] = False
        vd["motion_profile"] = prof
        vd["background_color"] = s["background_color"]
        vd.pop("background_variant", None)
        s["visual_design"] = vd
        mp = dict(s.get("motion_params") or {})
        mp["captionBottomPx"] = max(int(mp.get("captionBottomPx") or 400), 440)
        mp.setdefault("midSafeBottomRatio", 0.52)
        s["motion_params"] = mp
    return slides
