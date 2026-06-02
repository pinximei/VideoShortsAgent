from python_agent.platform_caption_presets import (
    apply_platform_caption_preset,
    apply_platform_presets_to_slides,
    reconcile_platform_slides,
)


def test_douyin_tiktok_preset():
    s = apply_platform_caption_preset({"type": "content_card"}, "douyin")
    assert s["caption_mode"] == "tiktok"
    assert s["caption_platform"] == "douyin"
    assert s["motion_params"]["maxCharsPerPage"] == 24
    assert s["motion_params"]["captionLineHeight"] == 1.06
    assert s["motion_params"]["captionLetterSpacing"] == 0
    assert s["visual_design"]["broadcast_frame"] is False


def test_douyin_reconcile_does_not_apply_shot_llm_here():
    """分镜 LLM 细设计在 slides_render，reconcile 只做版式/装饰骨架。"""
    slides = [
        {"type": "title_card"},
        {"type": "content_card", "scene_focus": True, "summary_lines": ["a", "b"]},
    ]
    out = reconcile_platform_slides(slides, "douyin")
    assert out[1].get("shot_design") is None


def test_douyin_reconcile_sparse_corners():
    slides = [
        {"type": "title_card"},
        {"type": "content_card", "scene_focus": True, "summary_lines": ["a", "b"]},
        {"type": "content_card", "scene_focus": True, "summary_lines": ["c", "d"]},
        {"type": "content_card", "scene_focus": True, "summary_lines": ["e", "f"]},
        {"type": "cta_card"},
    ]
    out = reconcile_platform_slides(slides, "douyin")
    corner_slides = [
        i for i, s in enumerate(out) if "corner-brackets" in (s.get("css_decorations") or [])
    ]
    assert len(corner_slides) <= 1
    assert corner_slides == [0]
    for s in out:
        if s.get("type") == "content_card":
            assert (s.get("visual_design") or {}).get("broadcast_frame") is False
            dec = set(s.get("css_decorations") or [])
            assert "grid-tunnel-bg" not in dec or "corner-brackets" not in dec


def test_xhs_max_chars_tighter():
    s = apply_platform_caption_preset({}, "xhs")
    assert s["motion_params"]["maxCharsPerPage"] == 12


def test_xhs_editorial_caption_and_light_bg():
    s = apply_platform_caption_preset({"type": "content_card"}, "xhs")
    assert s["caption_mode"] == "editorial"
    assert s["caption_platform"] == "xhs"
    assert s["motion_params"]["captionBottomPx"] >= 440
    assert s["motion_params"]["midSafeBottomRatio"] >= 0.5
    assert s["background_color"].lower().startswith("#f")
    assert s["visual_design"]["broadcast_frame"] is False


def test_xhs_title_may_have_broadcast():
    s = apply_platform_caption_preset({"type": "title_card"}, "xhs")
    assert s["visual_design"]["broadcast_frame"] is True


def test_xhs_reconcile_overrides_minimal_g():
    slides = [
        {
            "type": "content_card",
            "scene_focus": True,
            "motion_profile": "bullet_rail_right",
            "summary_lines": ["很长很长很长很长很长"],
            "mid_info_layout": "steps",
            "css_decorations": ["plain-white-bg"],
        }
    ]
    out = reconcile_platform_slides(slides, "xhs")
    assert out[0]["motion_profile"] == "tiktok_phrase_pages"
    assert out[0]["background_color"].lower() == "#f5f5f0"
    assert out[0]["visual_design"]["broadcast_frame"] is False
    assert len(out[0]["summary_lines"][0]) <= 10


def test_douyin_opening_frames_pinned():
    s = apply_platform_caption_preset({"type": "title_card"}, "douyin")
    assert int(s.get("opening_duration_frames") or 0) == 84


def test_cta_suppress_caption_on_douyin():
    s = apply_platform_caption_preset({"type": "cta_card"}, "douyin")
    assert s.get("suppress_bottom_caption") is True


def test_cta_suppress_caption_xhs():
    s = apply_platform_caption_preset({"type": "cta_card"}, "xhs")
    assert s.get("suppress_bottom_caption") is True


def test_batch_apply():
    out = apply_platform_presets_to_slides([{}, {}], "xhs")
    assert len(out) == 2
    assert out[0]["visual_design"]["color_mood"] == "xhs-soft"
