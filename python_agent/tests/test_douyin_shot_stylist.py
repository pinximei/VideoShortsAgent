from unittest.mock import patch

import pytest

from python_agent.douyin_shot_designer import DouyinShotDesignError
from python_agent.douyin_shot_stylist import (
    apply_douyin_shot_styles,
    github_daily_opening_hook,
)
from python_agent.eval_mock_compose import mock_compose_from_brief
from python_agent.tests.conftest_douyin_shot import mock_llm_shot_plans


def test_github_opening_includes_repo():
    h = github_daily_opening_hook(repo_name="OpenHands", stars="1.2万")
    assert "OpenHands" in h
    assert "GitHub" in h or "开源" in h


@patch(
    "python_agent.douyin_shot_designer.llm_design_all_shots",
    side_effect=mock_llm_shot_plans,
)
def test_compare_shot_via_llm(mock_llm):
    del mock_llm
    slides = [
        {"type": "title_card", "repo_name": "Bar"},
        {
            "type": "content_card",
            "scene_focus": True,
            "tts_text": "以前要半天，现在对比只要几分钟就完成。",
        },
        {"type": "content_card", "scene_focus": True, "tts_text": "第一步。"},
        {"type": "content_card", "scene_focus": True, "tts_text": "第二步。"},
    ]
    out = apply_douyin_shot_styles(slides, {"repo_name": "Bar"})
    layouts = {
        s.get("mid_info_layout")
        for s in out
        if s.get("scene_focus") or s.get("type") == "content_card"
    }
    assert len(layouts) >= 2


@patch(
    "python_agent.douyin_shot_designer.llm_design_all_shots",
    side_effect=mock_llm_shot_plans,
)
def test_mock_compose_then_llm_apply(mock_llm):
    del mock_llm
    brief = {
        "repo_name": "OpenHands",
        "stars": "12000",
        "feed_kind": "github_daily",
        "talking_points": ["a" * 20, "b" * 20, "c" * 20],
    }
    slides = mock_compose_from_brief(brief)["slides"]
    out = apply_douyin_shot_styles(slides, brief)
    assert all(s.get("shot_design_source") == "llm_shot_designer" for s in out if s.get("shot_design"))


def test_no_llm_raises():
    with patch("python_agent.douyin_shot_designer._llm_client", return_value=(None, None)):
        with pytest.raises(DouyinShotDesignError):
            apply_douyin_shot_styles(
                [{"type": "content_card", "scene_focus": True, "tts_text": "x"}],
                {},
            )
