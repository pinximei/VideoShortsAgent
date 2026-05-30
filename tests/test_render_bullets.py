"""要点字幕与 bullets 解析。"""
from __future__ import annotations

from python_agent.capabilities.registry import merge_render_effects
from python_agent.capabilities.clip_text import clip_bullets as _clip_bullets


def test_clip_bullets_from_list() -> None:
    clip = {"bullets": ["订阅变现", "开源 MIT"]}
    assert _clip_bullets(clip) == ["订阅变现", "开源 MIT"]


def test_clip_bullets_from_hook_separators() -> None:
    clip = {"hook_text": "省时间·易上手·可商用"}
    assert len(_clip_bullets(clip)) == 3


def test_apps_merge_content_highlight() -> None:
    clips = [{"start": 0, "end": 10, "hook_text": "x", "transition_to_next": "fade"}]
    fx = merge_render_effects("douyin", clips, {"preset": "科技"}, feed_kind="apps")
    assert fx["content_highlight"] is True

    news = merge_render_effects("douyin", clips, {"preset": "严肃"}, feed_kind="news")
    assert news["content_highlight"] is False
