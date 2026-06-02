from python_agent.layout_collision import (
    check_slide_layout_collision,
    fix_slide_layout_collision,
)
from python_agent.subtitle_copy import bind_motion_profile_to_layout, normalize_subtitle_cards


def test_layout_collision_detects_tight_gap():
    slide = {
        "type": "content_card",
        "scene_focus": True,
        "feature_label": "测试标题",
        "summary_lines": ["子标题一", "子标题二", "子标题三"],
        "viz_type": "stat",
        "stat_value": "12k",
        "motion_params": {
            "midSafeTopRatio": 0.14,
            "midSafeBottomRatio": 0.36,
            "captionBottomPx": 280,
        },
    }
    report = check_slide_layout_collision(slide, height=1920)
    assert report.get("ok") is False or report.get("gap_px", 999) < 48


def test_fix_collision_adjusts_motion_params():
    slide = {
        "type": "content_card",
        "scene_focus": True,
        "summary_lines": ["子一", "子二", "子三", "子四"],
        "feature_label": "主标题",
        "viz_type": "stat",
        "stat_value": "99k",
        "motion_params": {
            "midSafeTopRatio": 0.14,
            "midSafeBottomRatio": 0.36,
            "captionBottomPx": 280,
        },
    }
    fixed = fix_slide_layout_collision(slide)
    mp = fixed.get("motion_params") or {}
    assert fixed.get("_layout_collision_fixed") or mp.get("midSafeBottomRatio", 0) >= 0.4


def test_bind_motion_profile_steps():
    s = bind_motion_profile_to_layout(
        {"mid_info_layout": "steps", "motion_profile": "tiktok_phrase_pages"}
    )
    assert s["motion_profile"] == "bullet_stagger_up"


def test_slot_fallbacks():
    _, subs = normalize_subtitle_cards("主标题", [], tts="主标题口播很长的一段")
    assert len(subs) >= 2
    assert subs[0] in ("解决痛点", "核心能力", "立刻见效", "核心能力", "一步上手")
