from python_agent.subtitle_copy import (
    ensure_douyin_content_diversity,
    normalize_subtitle_cards,
    normalize_slide_mid_copy,
)


def test_dedupe_hero_and_subtitle():
    h, subs = normalize_subtitle_cards(
        "自然语言生成",
        ["自然语言生成", "说清需求", "直接运行"],
    )
    assert h == "自然语言生成"
    assert "自然语言生成" not in subs
    assert len(subs) >= 3


def test_subtitle_length_clamp():
    _, subs = normalize_subtitle_cards("主标题", ["短", "这是一条明显超过十四字限制的子标题文案"])
    assert all(4 <= len(x) <= 14 for x in subs)


def test_normalize_slide_mid_copy_stagger():
    s = normalize_slide_mid_copy(
        {
            "feature_label": "OpenHands",
            "summary_lines": ["OpenHands", "本机运行"],
            "motion_params": {},
        }
    )
    assert s["feature_label"] == "OpenHands"
    assert "OpenHands" not in (s.get("summary_lines") or [])
    assert int(s["motion_params"]["staggerFrames"]) >= 18


def test_ensure_douyin_content_diversity():
    slides = [
        {"type": "content_card", "scene_focus": True, "mid_info_layout": "steps", "motion_profile": "glass_card_stack"},
        {"type": "content_card", "scene_focus": True, "mid_info_layout": "steps", "motion_profile": "glass_card_stack"},
    ]
    out = ensure_douyin_content_diversity(slides)
    layouts = {s["mid_info_layout"] for s in out}
    assert len(layouts) >= 2
