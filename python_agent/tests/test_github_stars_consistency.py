from python_agent.douyin_shot_stylist import build_github_daily_hook_beats, format_stars_display, parse_star_count
from python_agent.github_stars_consistency import (
    audit_star_labels,
    validate_stars_consistency,
)
from python_agent.pinned_regression import validate_pinned_douyin_plan


def test_hook_beats_two_items():
    beats = build_github_daily_hook_beats(
        repo_name="OpenHands",
        stars="1.2万",
    )
    assert len(beats) == 2
    assert all(3 <= len(b) <= 18 for b in beats)


def test_stars_consistency_detects_mismatch():
    brief = {"stars": "1.2万", "feed_kind": "github_daily"}
    slides = [
        {"star_count": 12000, "stat_value": "1.2万"},
        {"star_count": 13000, "stat_value": "1.3万"},
    ]
    errs = validate_stars_consistency(slides, brief)
    assert any("mismatch" in e for e in errs)


def test_stars_sync_audit_ok():
    n = parse_star_count("1.2万")
    label = format_stars_display(n)
    slides = [{"star_count": n, "stat_value": label}]
    audit = audit_star_labels(slides, {"stars": "1.2万"})
    assert audit["ok"]


def test_pinned_plan_minimal():
    slides = [
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
            "summary_reveal_frames": [30, 60, 90],
            "_tts_sentences_bound": True,
            "motion_params": {"midSafeTopRatio": 0.14, "midSafeBottomRatio": 0.42, "captionBottomPx": 300},
        },
        {"type": "cta_card", "suppress_bottom_caption": True},
    ]
    reg = validate_pinned_douyin_plan(slides, brief={"feed_kind": "github_daily", "stars": "1.2万"})
    assert reg["ok"] or "star" not in str(reg.get("errors"))
