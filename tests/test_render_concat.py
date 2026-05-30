"""拼接转场与特效合并。"""
from __future__ import annotations

from python_agent.capabilities.registry import merge_render_effects
from python_agent.skills.render_skill import RenderSkill


def test_build_transition_intro_uses_fade() -> None:
    rs = RenderSkill.__new__(RenderSkill)
    tr = rs._build_transition_list(
        3,
        [{"transition_to_next": "circleopen"}, {"transition_to_next": "fade"}],
        {"transition": "slideup"},
        bookend_prefix_len=1,
    )
    assert tr[0] == "fade"
    assert tr[1] == "circleopen"


def test_merge_apps_caption_remotion_off() -> None:
    clips = [{"start": 0, "end": 10, "hook_text": "x", "transition_to_next": "fade"}]
    fx = merge_render_effects("douyin", clips, {"preset": "科技"}, feed_kind="apps", use_remotion=True)
    assert fx["use_remotion"] is True
    assert fx["caption_remotion"] is False
    assert fx["gradient"] is False
