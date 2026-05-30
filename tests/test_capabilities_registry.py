"""VSA 能力目录与 merge_render_effects。"""
from __future__ import annotations

from python_agent.capabilities.registry import (
    EFFECT_SELECTION_RULES,
    merge_render_effects,
    resolve_transition,
    suggest_preset_for_feed,
    valid_transitions,
)


def test_valid_transitions_includes_dissolve() -> None:
    assert "dissolve" in valid_transitions()
    assert "fade" in valid_transitions()


def test_resolve_transition_fallback() -> None:
    assert resolve_transition("unknown_xyz", default="fade") == "fade"
    assert resolve_transition("dissolve") == "dissolve"


def test_merge_requires_preset_and_normalizes_last_transition() -> None:
    clips = [
        {"start": 0, "end": 10, "hook_text": "a", "transition_to_next": "circleopen"},
        {"start": 10, "end": 20, "hook_text": "b", "transition_to_next": "pixelize"},
    ]
    fx = merge_render_effects("douyin", clips, {"gradient": True}, feed_kind="apps")
    assert fx["preset"] in ("科技", "活力", "情感", "叙事", "严肃")
    assert clips[-1]["transition_to_next"] == "fade"
    assert fx["gradient"] is True


def test_merge_news_feed_suggests_serious_preset() -> None:
    clips = [{"start": 0, "end": 10, "hook_text": "x", "transition_to_next": "wipeleft"}]
    fx = merge_render_effects("xhs", clips, {}, feed_kind="news")
    assert fx["preset"] == "严肃"
    assert fx["gradient"] is False


def test_merge_news_forces_gradient_off_even_if_llm_requests() -> None:
    clips = [{"start": 0, "end": 10, "hook_text": "x", "transition_to_next": "fade"}]
    fx = merge_render_effects(
        "xhs",
        clips,
        {"preset": "情感", "gradient": True},
        feed_kind="news",
    )
    assert fx["gradient"] is False


def test_bookends_douyin_only() -> None:
    clips = [{"start": 0, "end": 10, "hook_text": "x", "transition_to_next": "fade"}]
    dy = merge_render_effects("douyin", clips, {"preset": "活力", "intro_card": True}, bookends="douyin")
    xh = merge_render_effects("xhs", clips, {"preset": "情感", "intro_card": True}, bookends="douyin")
    assert dy["intro_card"] is True
    assert xh["intro_card"] is False


def test_llm_section_has_rules() -> None:
    from python_agent.capabilities.registry import llm_capabilities_section

    s = llm_capabilities_section(feed_kind="apps")
    assert "effects.preset" in s or "preset" in s
    assert EFFECT_SELECTION_RULES.splitlines()[0] in s
