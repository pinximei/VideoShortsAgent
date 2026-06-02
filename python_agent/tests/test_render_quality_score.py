from python_agent.render_quality_score import score_douyin_render


def _good_slides():
    return [
        {
            "type": "title_card",
            "hook_beats": ["别划走", "Star1.2万"],
            "opening_duration_frames": 84,
        },
        {
            "type": "content_card",
            "scene_focus": True,
            "feature_label": "自然语言生成",
            "summary_lines": ["本机部署", "一步上手", "值得收藏"],
            "summary_reveal_frames": [20, 50, 80],
            "_tts_sentences_bound": True,
            "motion_profile": "glass_card_stack",
            "motion_params": {
                "midSafeTopRatio": 0.14,
                "midSafeBottomRatio": 0.42,
                "captionBottomPx": 300,
            },
        },
        {
            "type": "content_card",
            "scene_focus": True,
            "feature_label": "办公自动化",
            "summary_lines": ["省时省力", "立刻见效", "值得试试"],
            "summary_reveal_frames": [20, 50, 80],
            "_tts_sentences_bound": True,
            "motion_profile": "bullet_stagger_up",
            "motion_params": {
                "midSafeTopRatio": 0.14,
                "midSafeBottomRatio": 0.42,
                "captionBottomPx": 300,
            },
        },
        {"type": "cta_card", "suppress_bottom_caption": True},
    ]


def test_high_score_clean_plan():
    out = score_douyin_render(_good_slides(), gate={"ok": True, "warnings": [], "errors": []})
    assert out["score"] >= 75
    assert out["grade"] in ("A", "B")


def test_deduct_generic_hero():
    slides = _good_slides()
    slides[1]["feature_label"] = "核心亮点"
    slides[1]["heading"] = "核心亮点"
    out = score_douyin_render(slides, gate={"ok": False, "errors": ["x"], "warnings": []})
    assert out["score"] < 90
    assert not out["pass"]
