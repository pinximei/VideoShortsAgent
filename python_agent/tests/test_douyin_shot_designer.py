from unittest.mock import patch

import pytest

from python_agent.douyin_shot_designer import (
    DouyinShotDesignError,
    analyze_tts_signals,
    build_all_shot_plans,
    build_content_shot_plans,
    design_shot_from_content,
)
from python_agent.douyin_shot_stylist import apply_douyin_shot_styles
from python_agent.tests.conftest_douyin_shot import mock_llm_shot_plans


def test_signals_compare():
    sig = analyze_tts_signals("以前要半天，现在一键对比就搞定")
    assert sig.has_compare


def test_requires_llm_key():
    with patch("python_agent.douyin_shot_designer._llm_client", return_value=(None, None)):
        with pytest.raises(DouyinShotDesignError, match="llm_api_key"):
            build_all_shot_plans([], {})


@patch(
    "python_agent.douyin_shot_designer.llm_design_all_shots",
    side_effect=mock_llm_shot_plans,
)
def test_llm_only_three_layouts(mock_llm):
    del mock_llm
    slides = [
        {"type": "title_card", "heading": "Foo", "repo_name": "Foo"},
        {"type": "content_card", "scene_focus": True, "tts_text": "Star 破万。"},
        {"type": "content_card", "scene_focus": True, "tts_text": "第一步写需求。"},
        {"type": "content_card", "scene_focus": True, "tts_text": "以前慢现在快对比。"},
    ]
    plans = build_content_shot_plans(slides, {"repo_name": "Foo"})
    layouts = {plans[i].mid_info_layout for i in plans}
    assert len(layouts) >= 2


@patch(
    "python_agent.douyin_shot_designer.llm_design_all_shots",
    side_effect=mock_llm_shot_plans,
)
def test_apply_llm_only(mock_llm):
    del mock_llm
    slides = [
        {"type": "title_card", "heading": "Foo", "repo_name": "Foo"},
        {
            "type": "content_card",
            "scene_focus": True,
            "tts_text": "Star 还在涨，GitHub 上热度很高。",
        },
    ]
    out = apply_douyin_shot_styles(slides, {"repo_name": "Foo", "stars": "8000"})
    assert out[1].get("shot_design_source") == "llm_shot_designer"
    assert "odometer-stars" in (out[1].get("css_decorations") or [])


def test_design_rules_still_unit_testable():
    d = design_shot_from_content(
        tts="对比前后效率",
        brief={},
        shot_index=0,
        used_layouts=set(),
        used_effects=set(),
        used_profiles=set(),
    )
    assert d.mid_info_layout == "compare"
