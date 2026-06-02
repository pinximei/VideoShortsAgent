import json
from pathlib import Path

from python_agent.caption_region_audit import plan_caption_risks
from python_agent.douyin_offline_loop import evaluate_variant, _variant_baseline


def _slides():
    return [
        {"type": "title_card", "hook_beats": ["a", "b"], "opening_duration_frames": 84},
        {
            "type": "content_card",
            "scene_focus": True,
            "feature_label": "测试标题",
            "summary_lines": ["子标题一", "子标题二", "子标题三"],
            "tts_text": "口播测试内容足够长",
            "motion_params": {"midSafeBottomRatio": 0.36, "captionBottomPx": 270},
        },
        {"type": "cta_card", "suppress_bottom_caption": True},
    ]


def test_evaluate_variant_baseline():
    r = evaluate_variant(_slides(), "baseline", _variant_baseline, brief={"feed_kind": "github_daily"})
    assert "score" in r
    assert int(r["score"]["score"]) >= 0


def test_plan_caption_risks_empty_when_ok():
    slides = _slides()
    for s in slides:
        if s.get("scene_focus"):
            s["motion_params"] = {
                "midSafeTopRatio": 0.14,
                "midSafeBottomRatio": 0.34,
                "captionBottomPx": 260,
            }
    issues = plan_caption_risks(slides)
    assert isinstance(issues, list)
