"""十轮十角色评审与十种排型。"""
from __future__ import annotations

from python_agent.douyin_layout_registry import DOUYIN_CONTENT_LAYOUTS, layout_for_content_index
from python_agent.douyin_cycle_review import ROLE_SPECS, cycle_context, run_role_review_rounds
from python_agent.eval_mock_compose import mock_compose_from_brief
from python_agent.platform_caption_presets import reconcile_platform_slides


def test_ten_layout_catalog():
    assert len(DOUYIN_CONTENT_LAYOUTS) == 10
    ids = {x["id"] for x in DOUYIN_CONTENT_LAYOUTS}
    assert len(ids) == 10


def test_ten_agent_rounds_complete():
    brief = {"platform": "douyin", "feed_kind": "github_daily"}
    slides = reconcile_platform_slides(mock_compose_from_brief(brief)["slides"], "douyin")
    ctx = cycle_context(1)
    out, logs, pre = run_role_review_rounds(slides, ctx)
    assert len(logs) == 10
    assert len(ROLE_SPECS) == 10
    assert logs[0]["role"] == "抖音运营"
    assert logs[9]["role"] == "QA总监"


def test_cycle2_has_layout_opinions():
    slides = reconcile_platform_slides(
        mock_compose_from_brief({"platform": "douyin", "feed_kind": "github_daily"})["slides"],
        "douyin",
    )
    _, _, pre = run_role_review_rounds(slides, cycle_context(2))
    assert any("L04" in x or "L05" in x or "profile" in x or "stagger" in x for x in pre)


def test_reconcile_uses_ten_layouts():
    brief = {"platform": "douyin", "feed_kind": "github_daily"}
    slides = mock_compose_from_brief(brief)["slides"]
    out = reconcile_platform_slides(slides, "douyin")
    content = [s for s in out if s.get("scene_focus") or str(s.get("type")) == "content_card"]
    assert len(content) >= 2
    profiles = {s.get("motion_profile") for s in content}
    assert len(profiles) >= 2
    assert int((content[0].get("motion_params") or {}).get("staggerFrames") or 0) >= 18


def test_layout_index_cycles():
    a = layout_for_content_index(0)["id"]
    b = layout_for_content_index(10)["id"]
    assert a == b
