from python_agent.platform_caption_presets import (
    apply_platform_caption_preset,
    apply_platform_presets_to_slides,
)


def test_douyin_tiktok_preset():
    s = apply_platform_caption_preset({"type": "content_card"}, "douyin")
    assert s["caption_mode"] == "tiktok"
    assert s["caption_platform"] == "douyin"
    assert s["motion_params"]["maxCharsPerPage"] == 18


def test_xhs_semantic_preset():
    s = apply_platform_caption_preset({}, "xhs")
    assert s["caption_mode"] == "semantic"
    assert s["caption_platform"] == "xhs"
    assert s["motion_params"]["captionFontScale"] == 0.72


def test_batch_apply():
    out = apply_platform_presets_to_slides([{}, {}], "xhs")
    assert len(out) == 2
    assert out[0]["visual_design"]["color_mood"] == "cool"
